"""Read-only production snapshot -> disposable local PostgreSQL, never an app.

Run only in the approved Render service after installing matching PostgreSQL tools.
The target is generated here; it cannot be supplied by the operator. No network
listener, provider/mail/AI process or production write is started. All scratch
copies are removed, even on failure. Output contains aggregate evidence only.
This tests a fresh logical snapshot, not Render's managed PITR/snapshot product.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time


SERVICE = 'srv-d9rqg6navr4c739thoeg'


class PostgreSQLCommandError(RuntimeError):
    def __init__(self, tool, stderr):
        self.tool=tool
        message=stderr.decode('utf-8',errors='replace').lower()
        self.kind=next((code for needle,code in (
            ('schema "public" already exists','existing_default_schema'),
            ('permission denied','permission_denied'),
            ('does not exist','missing_dependency'),
            ('unrecognized configuration parameter','version_mismatch'),
            ('connection to server','connection_failed'),
        ) if needle in message),'command_failed')
        super().__init__('PostgreSQL command failed')


def media_path(root, value):
    root = Path(root).resolve(strict=True)
    raw = Path(value)
    if not raw.is_absolute():
        raw = Path.cwd() / raw
    resolved = raw.resolve()
    if not resolved.is_relative_to(root) or resolved == root or raw.is_symlink():
        raise ValueError('Media is outside the approved upload directory')
    resolved = resolved.resolve(strict=True)
    if not resolved.is_file():
        raise ValueError('Media is not a regular file')
    return resolved


def file_digest(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def backup_media(upload_root, media, destination):
    """Keep missing historical records visible while still testing the database."""
    receipts=[];total=0;missing=0
    for index,(storage_key,size_bytes) in enumerate(media):
        try:original=media_path(upload_root,storage_key)
        except FileNotFoundError:
            missing+=1
            continue
        total+=original.stat().st_size
        if total>512*1024*1024:
            raise ValueError('Uploads exceed this bounded rehearsal size')
        backup=Path(destination)/str(index)
        before=file_digest(original)
        shutil.copyfile(original,backup);os.chmod(backup,0o600)
        if file_digest(original)!=before or file_digest(backup)!=before or backup.stat().st_size!=size_bytes:
            raise ValueError('Media changed or mismatched')
        receipts.append((backup,before))
    return receipts,total,missing


def table_manifest(connection):
    from psycopg import sql
    tables = connection.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename").fetchall()
    result = {}
    for (name,) in tables:
        # Hash unordered rows; never return customer fields to logs or the receipt.
        rows = connection.execute(sql.SQL('SELECT row_to_json(t)::text FROM {} t').format(sql.Identifier('public', name)))
        digests = sorted(hashlib.sha256(row[0].encode()).digest() for row in rows)
        result[name] = {'rows':len(digests), 'sha256':hashlib.sha256(b''.join(digests)).hexdigest()}
    return result


def local_environment(extra=None):
    # No inherited database, mail, session, billing or provider credentials.
    result = {'PATH':os.environ.get('PATH','/usr/bin:/bin'), 'LANG':'C.UTF-8',
              'LC_ALL':'C.UTF-8', 'TZ':'UTC'}
    if extra:
        result.update(extra)
    return result


def target_connection(root):
    """The only restore destination is a private Unix socket inside scratch."""
    root = Path(root).resolve(strict=True)
    if root.parent != Path('/tmp') or not root.name.startswith('zova-recovery-'):
        raise ValueError('Unexpected recovery destination')
    return {'host':str(root/'socket'), 'port':55439, 'dbname':'zova_recovery', 'user':'zova_recovery'}


def run(pg_bin):
    import psycopg
    from psycopg import sql
    from psycopg.conninfo import conninfo_to_dict
    from cryptography.fernet import Fernet, InvalidToken

    if os.name != 'posix' or os.environ.get('RENDER_SERVICE_ID') != SERVICE:
        raise ValueError('Requires the named Render service')
    if os.environ.get('ZOVA_RESTORE_ALLOW_LIVE_READ') != 'approved-isolated-rehearsal':
        raise ValueError('Explicit isolated rehearsal acknowledgement required')
    if os.environ.get('S3_BUCKET'):
        raise ValueError('This rehearsal only supports the existing local upload disk')
    source_url = os.environ['DATABASE_URL'].replace('postgresql+psycopg://','postgresql://')
    source_options = conninfo_to_dict(source_url)
    if not source_options.get('host') or source_options['host'] in {'localhost','127.0.0.1'}:
        raise ValueError('Expected the existing managed production source')
    bin_path = Path(pg_bin).resolve(strict=True)
    for command in ('pg_dump','pg_restore','pg_ctl','initdb','postgres'):
        if not (bin_path/command).is_file():
            raise ValueError('Missing PostgreSQL tools')
    upload_root = Path(os.environ.get('UPLOAD_DIR','/app/uploads')).resolve(strict=True)
    if upload_root != Path('/app/uploads'):
        raise ValueError('Unexpected production upload root')
    if shutil.disk_usage('/tmp').free < 512 * 1024 * 1024:
        raise ValueError('Insufficient scratch capacity')
    memory_limit = Path('/sys/fs/cgroup/memory.max')
    memory_used = Path('/sys/fs/cgroup/memory.current')
    if memory_limit.exists() and memory_limit.read_text().strip().isdigit():
        if int(memory_limit.read_text())-int(memory_used.read_text()) < 192*1024*1024:
            raise ValueError('Insufficient memory headroom for isolated PostgreSQL')

    started = time.monotonic()
    root = Path(tempfile.mkdtemp(prefix='zova-recovery-', dir='/tmp')).resolve()
    uid, gid = (65534,65534) if os.getuid()==0 else (os.getuid(),os.getgid())
    os.chown(root,uid,gid)
    os.chmod(root,0o700)
    for folder in ('socket','media'):
        path=root/folder;path.mkdir(mode=0o700);os.chown(path,uid,gid)
    stage='preflight'
    server_started=False
    receipt={'status':'failed','source_writes':False,'application_started':False,
             'provider_calls':False,'managed_snapshot_restore':False}

    def command(name, arguments, *, env=None, local=True, timeout=120):
        kwargs={'user':uid,'group':gid} if local and os.getuid()==0 else {}
        tool_env=dict(env or local_environment())
        # Supports signed packages extracted in scratch, without installing a
        # database service or changing the live container's system libraries.
        library_path=bin_path.parents[3]/'lib'/'x86_64-linux-gnu'
        if library_path.is_dir():tool_env['LD_LIBRARY_PATH']=str(library_path)
        completed=subprocess.run([str(bin_path/name),*arguments],cwd=root,
            env=tool_env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
            timeout=timeout,**kwargs)
        if completed.returncode:
            # Driver output can include identifiers. Keep it out of console evidence.
            raise PostgreSQLCommandError(name,completed.stderr)
        return completed.stdout

    try:
        stage='snapshot'
        with psycopg.connect(source_url, options='-c default_transaction_read_only=on -c statement_timeout=30000 -c timezone=UTC') as source:
            source.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
            source_version=int(source.execute("SHOW server_version_num").fetchone()[0])//10000
            size=source.execute('SELECT pg_database_size(current_database())').fetchone()[0]
            if size > 128*1024*1024:
                raise ValueError('Database exceeds this bounded rehearsal size')
            snapshot=source.execute('SELECT pg_export_snapshot()').fetchone()[0]
            source_manifest=table_manifest(source)
            pg_env=local_environment({'PG'+key.upper():value for key,value in source_options.items()
                                     if key in {'host','port','user','password','dbname','sslmode','sslrootcert'}})
            pg_env['PGDATABASE']=pg_env.pop('PGDBNAME',source_options.get('dbname',''))
            pg_env['PGOPTIONS']='-c default_transaction_read_only=on -c statement_timeout=30000'
            pg_env['PGCONNECT_TIMEOUT']='10'
            stage='logical_backup'
            dump=root/'snapshot.dump'
            command('pg_dump',['--format=custom','--schema=public','--no-owner','--no-privileges',
                '--lock-wait-timeout=5000','--snapshot='+snapshot,'--file='+str(dump)],env=pg_env,local=False)
            pg_env.clear()
            os.chown(dump,uid,gid);os.chmod(dump,0o600)
            stage='media_backup'
            media=source.execute('SELECT storage_key,size_bytes FROM nova_media_assets ORDER BY id').fetchall()
            media_receipts,total,missing=backup_media(upload_root,media,root/'media')
            receipt['missing_media_records']=missing
        # The source read transaction is closed before starting the scratch server.
        stage='isolated_server'
        command('initdb',['-D',str(root/'pgdata'),'-U','zova_recovery','--auth=trust',
                          '--no-locale','--encoding=UTF8'])
        command('pg_ctl',['-D',str(root/'pgdata'),'-l',str(root/'postgres.log'),'-w','start','-o',
            "-p 55439 -k " + str(root/'socket') + " -c listen_addresses='' -c shared_buffers=16MB"
            " -c max_connections=10 -c max_wal_size=64MB -c min_wal_size=32MB -c jit=off"])
        server_started=True
        local=target_connection(root)
        with psycopg.connect(**{**local,'dbname':'postgres'},autocommit=True) as admin:
            if Path(admin.execute('SHOW data_directory').fetchone()[0]).resolve()!=root/'pgdata':
                raise ValueError('Local database identity mismatch')
            if admin.execute('SHOW listen_addresses').fetchone()[0]!='':
                raise ValueError('Scratch database must not have a network listener')
            admin.execute('CREATE DATABASE zova_recovery')
        stage='database_restore'
        # A schema-only-filtered dump includes CREATE SCHEMA public. The target
        # is this invocation's newly created, identity-checked scratch database.
        command('pg_restore',['--host='+local['host'],'--port=55439','--username=zova_recovery',
            '--dbname=zova_recovery','--no-owner','--no-privileges','--clean','--if-exists','--exit-on-error',str(dump)])
        stage='compare_and_decrypt'
        with psycopg.connect(**local,options='-c default_transaction_read_only=on -c timezone=UTC') as restored:
            if table_manifest(restored)!=source_manifest:
                raise ValueError('Restored table hashes differ from the consistent snapshot')
            fernet=Fernet(os.environ['CREDENTIAL_ENCRYPTION_KEY'].encode())
            wrong=Fernet(Fernet.generate_key())
            encrypted=restored.execute("SELECT table_name,column_name FROM information_schema.columns WHERE table_schema='public' AND column_name LIKE 'encrypted_%'").fetchall()
            decrypted=0
            for table,column in encrypted:
                values=restored.execute(sql.SQL('SELECT {} FROM {} WHERE {} IS NOT NULL').format(
                    sql.Identifier(column),sql.Identifier('public',table),sql.Identifier(column)))
                for (value,) in values:
                    if not value:continue
                    plaintext=fernet.decrypt(value.encode());decrypted+=1
                    del plaintext
                    try:wrong.decrypt(value.encode())
                    except InvalidToken:pass
                    else:raise ValueError('Wrong key was accepted')
            # A full row digest covers password hashes, auth versions, revocations,
            # consent, ownership, reviews, unknown receipts and deletion records.
            for backup,digest in media_receipts:
                recovered=backup.with_suffix('.restored')
                shutil.copyfile(backup,recovered);os.chmod(recovered,0o600)
                if file_digest(recovered)!=digest:raise ValueError('Media restore mismatch')
        receipt.update(status='incomplete' if missing else 'passed',database_restore='passed',
            media_restore='incomplete' if missing else 'passed',source_major=source_version,tables=len(source_manifest),
            rows=sum(t['rows'] for t in source_manifest.values()),encrypted_values_verified=decrypted,
            media_files=len(media_receipts),media_bytes=total,snapshot_sha256=file_digest(dump),
            consistent_snapshot=True,network_listener=False)
    except Exception as exc:
        receipt.update(failed_stage=stage,error_type=type(exc).__name__)
        if isinstance(exc,PostgreSQLCommandError):
            receipt.update(failed_tool=exc.tool,failure_kind=exc.kind)
    finally:
        if server_started:
            try:command('pg_ctl',['-D',str(root/'pgdata'),'-m','immediate','-w','stop'])
            except Exception:
                receipt.update(status='failed',cleanup='server_stop_failed')
        if receipt.get('cleanup')!='server_stop_failed':
            # Only this invocation's private mkdtemp path may be removed.
            if root.parent==Path('/tmp') and root.name.startswith('zova-recovery-') and not root.is_symlink():
                shutil.rmtree(root)
                receipt['scratch_removed']=not root.exists()
        receipt['elapsed_seconds']=round(time.monotonic()-started,2)
    print(json.dumps(receipt,sort_keys=True))
    return 0 if receipt['status']=='passed' and receipt.get('scratch_removed') else 1


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pg-bin',required=True)
    args=parser.parse_args()
    try:raise SystemExit(run(args.pg_bin))
    except (ValueError,KeyError,OSError) as exc:
        print(json.dumps({'status':'refused','error_type':type(exc).__name__}))
        raise SystemExit(1) from None
