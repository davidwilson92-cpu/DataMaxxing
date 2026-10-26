import json
import pytest
from scripts.aws_beta_entrypoint import configuration
from infra.aws.build_template import template


def settings(**changes):
    return json.dumps({'DATABASE_URL':'postgresql+psycopg://runtime:synthetic@synthetic.eu-west-2.rds.amazonaws.com/zova?sslmode=verify-full&sslrootcert=/app/infra/aws/eu-west-2-rds-ca.pem',
                      'SESSION_SECRET':'preserved-session',
                      'CREDENTIAL_ENCRYPTION_KEY':'preserved-encryption',
                      'STRIPE_SECRET_KEY':'sk_test_synthetic', **changes})


def test_import_preserves_auth_but_cannot_enable_charges_or_replace_workload_identity():
    result=configuration(settings(STRIPE_MODE='live', REQUIRE_SUBSCRIPTION='true',
                                  PUBLIC_BASE_URL='https://wrong.example', S3_BUCKET='old'))
    assert result['SESSION_SECRET']=='preserved-session'
    assert result['CREDENTIAL_ENCRYPTION_KEY']=='preserved-encryption'
    assert not {'STRIPE_MODE','REQUIRE_SUBSCRIPTION','PUBLIC_BASE_URL','S3_BUCKET'} & result.keys()
    for name in ('AWS_ACCESS_KEY_ID','LD_PRELOAD','PYTHONPATH','PATH','ZOVA_AWS_SETTINGS_SECRET_ARN'):
        with pytest.raises(ValueError): configuration(settings(**{name:'unexpected'}))
    with pytest.raises(ValueError):configuration(settings(STRIPE_SECRET_KEY='sk_live_synthetic'))
    with pytest.raises(ValueError):configuration(settings(DATABASE_URL='sqlite:///old.db'))
    with pytest.raises(ValueError):configuration(settings(DATABASE_URL='postgresql://runtime:synthetic@synthetic.eu-west-2.rds.amazonaws.com/zova?sslmode=require'))
    with pytest.raises(ValueError):configuration(settings(SESSION_SECRET=''))
    with pytest.raises(ValueError):configuration('["not an environment"]')


def test_infrastructure_starts_without_a_writer_and_keeps_customer_stores_private():
    stack=template(); resources=stack['Resources']
    assert stack['Parameters']['DesiredCount']['Default']==0
    assert stack['Parameters']['DesiredCount']['AllowedValues']==[0,1]
    assert stack['Parameters']['SchedulerMode']['Default']=='disabled'
    assert stack['Parameters']['MaintenanceMode']['Default']=='cloud-migration'
    assert stack['Parameters']['PostgresVersion']['Default']=='18.6'
    assert resources['DatabaseParameters']['Properties']['Family']=='postgres18'
    db=resources['Database']['Properties']
    assert db['PubliclyAccessible'] is False and db['StorageEncrypted'] is True
    assert db['DeletionProtection'] and db['BackupRetentionPeriod']>=7
    for name in ('Database','Files','Uploads','Images','Logs'):
        assert resources[name]['DeletionPolicy']=='Retain'
    assert resources['Files']['Properties']['Encrypted']
    task=resources['Task']['Properties']; volume=task['Volumes'][0]['EFSVolumeConfiguration']
    assert volume['TransitEncryption']=='ENABLED' and volume['AuthorizationConfig']['IAM']=='ENABLED'
    service=resources['Service']['Properties']
    assert not service['EnableExecuteCommand']
    assert service['DeploymentConfiguration']['MaximumPercent']==100
    env={row['Name']:row['Value'] for row in task['ContainerDefinitions'][0]['Environment']}
    assert env['REQUIRE_SUBSCRIPTION']==env['STRIPE_LIVE_CHECKOUT_ENABLED']=='false'
    assert env['STRIPE_MODE']=='test' and env['PUBLIC_BASE_URL']=='https://zova-social.com'
    statements=resources['AppRole']['Properties']['Policies'][0]['PolicyDocument']['Statement']
    assert all(s['Resource']!='*' for s in statements)


def test_generated_deployment_matches_reviewed_source_and_uses_official_ca():
    from pathlib import Path
    import hashlib
    root=Path(__file__).resolve().parents[1]
    assert json.loads((root/'infra/aws/beta.template.json').read_text())==template()
    ca=(root/'infra/aws/eu-west-2-rds-ca.pem').read_bytes()
    assert hashlib.sha256(ca).hexdigest()=='17c557502061c4879b844fff983288a2fb07d520f4cf2a5de60f5cda800a4494'


def test_settings_load_failure_does_not_disclose_secret(monkeypatch):
    import boto3
    from scripts.aws_beta_entrypoint import main
    monkeypatch.setenv('ZOVA_AWS_SETTINGS_SECRET_ARN','synthetic-secret')
    def unavailable(*args,**kwargs):raise RuntimeError('sensitive-synthetic-value')
    monkeypatch.setattr(boto3,'client',unavailable)
    with pytest.raises(SystemExit) as failure:main()
    assert str(failure.value)=='AWS application settings could not be loaded; startup stopped.'


def test_only_load_balancer_peers_supply_the_real_client_and_ignore_spoofed_prefixes():
    import asyncio
    from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
    from scripts.aws_beta_entrypoint import TRUSTED_PROXIES
    observed=[]
    async def capture(scope, receive, send):observed.append(scope)
    middleware=ProxyHeadersMiddleware(capture,trusted_hosts=TRUSTED_PROXIES)
    for peer,expected,scheme in [('10.84.0.20','203.0.113.8','https'),('10.84.1.20','203.0.113.8','https'),('198.51.100.4','198.51.100.4','http')]:
        scope={'type':'http','client':(peer,1000),'scheme':'http','headers':[
            (b'x-forwarded-for',b'192.0.2.99, 203.0.113.8'),(b'x-forwarded-proto',b'https')]}
        asyncio.run(middleware(scope,None,None))
        assert observed[-1]['client'][0]==expected
        assert observed[-1]['scheme']==scheme


def test_cloud_copy_freeze_blocks_oauth_and_writes_without_authorising_erasure(monkeypatch):
    from test_account_integrity import account
    from nova.db import SessionLocal, User
    from nova.maintenance import account_erasure_mode
    from nova.runtime import validate_runtime
    client,uid,*_=account()
    monkeypatch.setenv('ZOVA_MAINTENANCE_MODE','cloud-migration')
    monkeypatch.setenv('ZOVA_SCHEDULER_MODE','disabled')
    assert validate_runtime()=='disabled' and not account_erasure_mode()
    for method,path in [('post','/account/profile'),('post','/api/media'),
                        ('post','/billing/webhook'),('get','/callback/instagram'),
                        ('get','/callback/facebook'),('get','/callback/x'),
                        ('get','/callback/tiktok'),('post','/mobile/web-session')]:
        response=getattr(client,method)(path)
        assert response.status_code==503 and response.headers['Cache-Control']=='no-store'
    assert client.get('/health').status_code==200
    assert client.get('/internal/maintenance').status_code==401
    monkeypatch.setenv('SCHEDULER_SECRET','synthetic-operator')
    status=client.get('/internal/maintenance',headers={'Authorization':'Bearer synthetic-operator'}).json()
    assert status['maintenance_mode']=='cloud-migration' and not status['account_erasure_mode']
    assert status['services_drained']=='operator_confirmation_required'
    with SessionLocal() as db:assert db.get(User,uid).display_name=='Original'
    monkeypatch.setenv('ZOVA_SCHEDULER_MODE','embedded')
    with pytest.raises(ValueError,match='disabled scheduling'):validate_runtime()
    monkeypatch.delenv('ZOVA_MAINTENANCE_MODE')
    assert client.get('/studio').status_code==200
