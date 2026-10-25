# AWS beta migration candidate — not deployed

Prepared 25 October 2026. Production remains on Render. The owner requested AWS
migration; the earlier Free-plan decision has not yet been replaced by a paid-plan
or spending approval. No credits have been assumed or awarded in this work.

## Proposed first destination

London (`eu-west-2`), one ECS Fargate web task (0.25 vCPU / 512 MiB), managed
PostgreSQL, HTTPS Application Load Balancer, encrypted regional EFS uploads,
ECR, scoped workload roles, Secrets Manager and 30-day application logs.
The iPhone app continues using `https://zova-social.com`; its backend moves with
the web app. Apple signing and TestFlight remain with Apple/Codemagic.

One task preserves the tested embedded scheduler. This is a small beta deployment,
not high availability or automatic scaling. Deployments stop the old task before
starting its replacement, avoiding concurrent embedded workers. Moving to multiple
web tasks requires the existing external-worker configuration plus a separately
validated shared-storage extension; do not increase DesiredCount beyond one.

EFS deliberately preserves existing `/app/uploads` file paths and media URLs,
including the current assisted deletion implementation. Moving directly to S3
would need a separate historical-URL and storage-erasure migration. Verify all
source storage paths before selecting this template; it is not a migration tool
for any already-S3-backed assets.

## Cost review, not a spending cap

Official AWS public price files retrieved 25 October 2026 for London:

| Resource | Rate | 730-hour estimate (USD) |
| --- | --- | --- |
| Fargate Linux x86 | $0.04656/vCPU-hour + $0.00511/GiB-hour | $10.36 |
| Application Load Balancer | $0.02646/hour | $19.32 |
| RDS PostgreSQL t4g.micro, single AZ | $0.018/hour | $13.14 |
| RDS gp3, 20 GiB | $0.133/GiB-month | $2.66 |
| EFS regional Standard | $0.33/GiB-month | Depends on uploads |

Allow roughly **$60–75/month** before credits/tax for a small beta, including an
allowance for public IPv4 addresses, secrets, modest load-balancer usage, logs,
EFS and backups. Transfer, CPU surplus, storage growth, build service, backups,
traffic and temporary overlap with Render add variable costs. This is an estimate,
not a quotation or a hard cap. The template's $75 account-wide budget emails
`david@zova-social.com` at 80%; it does **not** stop resources or spending.

Sources: AWS price-list JSON paths under
`https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/` for
`AmazonECS`, `AWSELB`, `AmazonRDS` and `AmazonEFS`, each
`current/eu-west-2/index.json`; [VPC pricing](https://aws.amazon.com/vpc/pricing/),
[Secrets Manager pricing](https://aws.amazon.com/secrets-manager/pricing/).
Confirm the account's plan, available credit, service eligibility, current regional
prices and approved budget before creating anything. Activate is not an awarded
credit balance; [Free-plan restrictions](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/free-tier-plans.html)
must be resolved before depending on it for continuous hosting.

## Deployable artifact and local checks

`build_template.py` generates `beta.template.json`; regenerate after source edits.
Use CloudFormation change sets and inspect IAM/network/retention changes before
execution. No script here submits a stack, exports secrets or changes DNS.

Defaults are **zero application tasks and disabled scheduling**. Existing validated
regional ACM certificate and application-settings secret ARNs are required.
The immutable image parameter may be a not-yet-built same-account ECR URI while
DesiredCount=0; update it to the successfully tested image digest after the stack's
repository exists and before starting any task. Never start a placeholder image.

The initial template selects PostgreSQL 17 family. **Read the production server
version first.** Select its supported minor version; if production uses a newer
major, update the template family/version constraint and revalidate instead of
downgrading. Check extension support, encoding, timezone and connection limits.

The AWS entrypoint imports preserved settings from the scoped secret; it refuses
static AWS credentials, execution-setting replacement, SQLite, live Stripe keys
and unverified RDS TLS. Use an AWS-managed-key secret (a custom KMS key needs a
separately reviewed decrypt policy). Its JSON must include a dedicated runtime
`DATABASE_URL`, the unchanged `SESSION_SECRET`, unchanged
`CREDENTIAL_ENCRYPTION_KEY`, and all existing operational/provider/mail settings.
Do not include AWS access keys or local execution variables. Domain, scheduler,
beta billing switches and upload root are fixed by the task, not the imported
Render configuration. Preserve all other source settings explicitly.

The runtime DB URL must use the actual London RDS hostname, URL-encoded
credentials and `sslmode=verify-full&sslrootcert=/app/infra/aws/eu-west-2-rds-ca.pem`.
The bundled CA comes from AWS's official London trust store; its SHA-256 is
`17c557502061c4879b844fff983288a2fb07d520f4cf2a5de60f5cda800a4494`.
Root filesystem is writable but the container runs as UID/GID 10001, has no
shell/SSH ingress or ECS Exec, and mounts uploads using encrypted IAM-authorized
EFS. No application IAM permission can read the RDS master secret.

## Required execution and evidence, in order

1. Sign in to existing AWS and Stripe accounts. Inspect existing resources and
   credits; approve the concrete hosting cost, new IAM roles, secret/data transfer
   and any plan upgrade before executing those actions. Keep customer charges off.
2. Inventory Render's actual DB version, size, source upload root, settings names,
   scheduled work, unknown provider outcomes and active social connections. Compare
   every source setting against the target. Never rotate encryption/session keys
   as part of migration. Preserve reviewer and beta accounts.
3. Prepare ACM DNS validation, the narrowly scoped app secret and a CloudFormation
   change set. Retained DB/files/images/logs must remain protected. Create the
   initial zero-task stack only after approvals. Verify no public database access,
   no SSH and no direct inbound task access outside the ALB security group.
4. Build the exact passing application commit into the stack's ECR repository;
   scan it and pin its digest. Test under UID 10001 with the EFS mount before use.
   Prepare a one-off, scoped migration task using the same private DB/EFS groups
   and a separate temporary maintenance role. Do not give web tasks DB-owner access.
5. Take an encrypted source backup and rehearse a restore into RDS. Restore with
   ownership/ACL handling reviewed; create a separate runtime login with only
   necessary table/sequence permissions, no superuser/DDL authority. Run additive
   candidate migrations offline using the maintenance identity; web uses verify
   mode. Confirm row counts and per-table content hashes, sequence positions and
   decryption of synthetic test credentials. Protect or remove private backup files
   under the approved retention plan; never commit them or print their contents.
6. Copy source uploads byte-for-byte into the EFS access point. Preserve paths,
   set files readable/writable by UID 10001 without public access, compare all
   checksums/sizes and reference counts. Record the four previously missing legacy
   uploads separately; do not invent replacements or call them restored. Confirm
   current drafts, attachments and deletion handling on disposable accounts.
7. Rehearse login/recovery, draft/media save and reopen, Schedule, Next move,
   mail delivery and each social OAuth return. Use the same public domain during
   the final verification; a preview hostname alone does not prove provider/iOS
   callbacks. No real social post without specific approval. Confirm Apple
   association endpoints and iOS API/session refresh. Test Stripe sandbox checkout,
   verified webhook sync, repeated return, portal/cancel and preserved free access.
8. Schedule a short write-freeze. **Do not run two independent writer databases.**
   Drain requests; pause Render's web writes and publishing process, then take the
   final consistent database/upload copy and verify it. Do not reuse the
   account-erasure maintenance flag as a migration mode. The implementation of a
   migration-specific write freeze remains an execution prerequisite, not an
   existing feature. Track in-flight provider outcomes and never blindly resend.
9. With Render writers stopped, start one AWS task with scheduling disabled,
   validate health/protected readiness, TLS, restored data and upload permissions.
   Change Cloudflare origin for `zova-social.com` only after verification. Keep
   callbacks, webhook URL and iOS server origin unchanged. Inspect all DNS records
   (including email and Apple association paths); do not replace the zone.
10. Verify web and installed iPhone app across real OAuth returns, existing/new
    sessions, reviewer access, media, scheduling and payment sandbox webhooks.
    Enable the AWS embedded scheduler only after confirming Render's is stopped.
    Record evidence/time/revision for every result. Watch errors and scheduled work.
11. Keep Render and the encrypted cutover backup for rollback; no deletion in this
    task. Before AWS accepts writes, DNS rollback can use the untouched source.
    **After AWS accepts writes**, freeze AWS and reconcile/restore the new data
    before switching back; pointing DNS at the old DB would lose customer changes.
    Revoke temporary migration permissions after verified completion.

## Outstanding external gates

AWS/Stripe sign-in, current Free/Paid plan and credits, spending/access approvals,
source inventory, database-major confirmation, build/restore/copy rehearsal,
migration write-freeze implementation, protected readiness, DNS cutover and real
device/provider checks are **not completed**. This template is reviewed preparation,
not evidence that AWS hosts Zova or that billing is live.
