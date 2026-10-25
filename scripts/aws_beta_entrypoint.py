"""Load the existing app settings from one scoped AWS secret, without logging them.

Used only by the AWS task definition. Render keeps its existing entrypoint.
The application domain, scheduler and beta billing switches belong to the task,
not to the imported Render secret. No AWS access keys are imported.
"""
import json
import os
import sys
from urllib.parse import parse_qs, urlsplit

PROTECTED = {
    'PUBLIC_BASE_URL', 'PORT', 'UPLOAD_DIR', 'ZOVA_SCHEDULER_MODE',
    'ZOVA_SCHEMA_MODE', 'ZOVA_WEB_REPLICAS', 'REQUIRE_SUBSCRIPTION',
    'STRIPE_MODE', 'STRIPE_LIVE_CHECKOUT_ENABLED', 'PLAN_LIMITS_ENABLED',
    'S3_BUCKET', 'S3_PUBLIC_BASE_URL', 'S3_ENDPOINT_URL',
    'ZOVA_MAINTENANCE_MODE',
}
PREFIXES = ('AWS_', 'PYTHON', 'LD_', 'DYLD_', 'ZOVA_AWS_')
TRUSTED_PROXIES = '10.84.0.0/24,10.84.1.0/24'


def configuration(raw):
    values = json.loads(raw)
    if not isinstance(values, dict) or not values or any(
        not isinstance(k, str) or not k.isidentifier() or not k.isupper()
        or not isinstance(v, str) or '\x00' in v for k, v in values.items()
    ):
        raise ValueError('Invalid application settings secret')
    forbidden = {'PATH', 'HOME', 'SHELL', 'BASH_ENV', 'ENV'}
    if any(k in forbidden or k.startswith(PREFIXES) for k in values):
        raise ValueError('Application settings cannot replace workload credentials or execution settings')
    result = {k: v for k, v in values.items() if k not in PROTECTED}
    for key in ('DATABASE_URL', 'SESSION_SECRET', 'CREDENTIAL_ENCRYPTION_KEY'):
        if not result.get(key):
            raise ValueError('Required application settings are missing')
    if not result['DATABASE_URL'].startswith(('postgresql://', 'postgresql+psycopg://')):
        raise ValueError('AWS beta requires PostgreSQL')
    database = urlsplit(result['DATABASE_URL'])
    tls = parse_qs(database.query)
    if (not (database.hostname or '').endswith('.eu-west-2.rds.amazonaws.com')
            or tls.get('sslmode') != ['verify-full']
            or tls.get('sslrootcert') != ['/app/infra/aws/eu-west-2-rds-ca.pem']):
        raise ValueError('AWS beta requires the London RDS endpoint and verified database TLS')
    key = result.get('STRIPE_SECRET_KEY', '')
    if key and not key.startswith(('sk_test_', 'rk_test_')):
        raise ValueError('AWS beta accepts Stripe test credentials only')
    return result


def main():
    import boto3
    try:
        arn = os.environ['ZOVA_AWS_SETTINGS_SECRET_ARN']
        response = boto3.client('secretsmanager').get_secret_value(SecretId=arn)
        values = configuration(response['SecretString'])
    except Exception:
        # SDK/JSON exceptions can contain credentials, endpoints or secret text.
        raise SystemExit('AWS application settings could not be loaded; startup stopped.') from None
    os.environ.update(values)
    os.execv(sys.executable, [sys.executable, '-m', 'uvicorn', 'app:app',
                            '--host', '0.0.0.0', '--port', os.environ.get('PORT', '10000'),
                            '--proxy-headers', '--forwarded-allow-ips', TRUSTED_PROXIES])


if __name__ == '__main__':
    main()
