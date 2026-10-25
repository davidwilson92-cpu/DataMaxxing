"""Generate the reviewable CloudFormation beta stack. Does not contact AWS.

One web task preserves the currently tested embedded publishing scheduler.
Encrypted shared EFS preserves historical upload paths and erasure behaviour.
The app starts at zero tasks; cutover is an explicit later stack update.
"""
import json
from pathlib import Path


def ref(name): return {'Ref': name}
def attr(name, value): return {'Fn::GetAtt': [name, value]}
def sub(value): return {'Fn::Sub': value}


def template():
    r = {}
    def add(name, kind, properties, retain=False, **extra):
        r[name] = {'Type': 'AWS::' + kind, 'Properties': properties, **extra}
        if retain:
            r[name].update(DeletionPolicy='Retain', UpdateReplacePolicy='Retain')
    add('Network', 'EC2::VPC', dict(CidrBlock='10.84.0.0/16', EnableDnsSupport=True, EnableDnsHostnames=True))
    add('Gateway', 'EC2::InternetGateway', {})
    add('GatewayAttachment', 'EC2::VPCGatewayAttachment', dict(VpcId=ref('Network'), InternetGatewayId=ref('Gateway')))
    add('Routes', 'EC2::RouteTable', dict(VpcId=ref('Network')))
    add('InternetRoute', 'EC2::Route', dict(RouteTableId=ref('Routes'), DestinationCidrBlock='0.0.0.0/0', GatewayId=ref('Gateway')), DependsOn='GatewayAttachment')
    for i in (0, 1):
        az = {'Fn::Select': [i, {'Fn::GetAZs': ''}]}
        for name, octet in [('Public', i), ('Private', i + 10)]:
            add(f'{name}{i}', 'EC2::Subnet', dict(VpcId=ref('Network'), CidrBlock=f'10.84.{octet}.0/24', AvailabilityZone=az, MapPublicIpOnLaunch=False))
        add(f'PublicRoute{i}', 'EC2::SubnetRouteTableAssociation', dict(SubnetId=ref(f'Public{i}'), RouteTableId=ref('Routes')))
    add('FrontGroup', 'EC2::SecurityGroup', dict(GroupDescription='HTTPS web entry; HTTP only redirects', VpcId=ref('Network'), SecurityGroupIngress=[dict(IpProtocol='tcp', FromPort=p, ToPort=p, CidrIp='0.0.0.0/0') for p in (80,443)]))
    add('AppGroup', 'EC2::SecurityGroup', dict(GroupDescription='Application only from load balancer', VpcId=ref('Network'), SecurityGroupIngress=[dict(IpProtocol='tcp', FromPort=10000, ToPort=10000, SourceSecurityGroupId=ref('FrontGroup'))]))
    for name, port in [('DatabaseGroup',5432), ('FilesGroup',2049)]:
        add(name, 'EC2::SecurityGroup', dict(GroupDescription='Private application access only', VpcId=ref('Network'), SecurityGroupIngress=[dict(IpProtocol='tcp', FromPort=port, ToPort=port, SourceSecurityGroupId=ref('AppGroup'))]))
    add('DatabaseSubnets', 'RDS::DBSubnetGroup', dict(DBSubnetGroupDescription='Private database subnets; no internet route', SubnetIds=[ref('Private0'),ref('Private1')]))
    add('DatabaseParameters', 'RDS::DBParameterGroup', dict(Description='Require encrypted database sessions', Family='postgres17', Parameters={'rds.force_ssl':'1'}))
    add('Database', 'RDS::DBInstance', dict(Engine='postgres', EngineVersion=ref('PostgresVersion'), DBInstanceClass='db.t4g.micro', AllocatedStorage='20', MaxAllocatedStorage=40, StorageType='gp3', StorageEncrypted=True, DBName='zova', MasterUsername='zova_owner', ManageMasterUserPassword=True, PubliclyAccessible=False, DBSubnetGroupName=ref('DatabaseSubnets'), DBParameterGroupName=ref('DatabaseParameters'), VPCSecurityGroups=[ref('DatabaseGroup')], BackupRetentionPeriod=7, CopyTagsToSnapshot=True, DeletionProtection=True, AutoMinorVersionUpgrade=True, MultiAZ=False), retain=True)
    add('Files', 'EFS::FileSystem', dict(Encrypted=True, PerformanceMode='generalPurpose', ThroughputMode='bursting', BackupPolicy={'Status':'ENABLED'}, FileSystemPolicy={'Statement':[{'Effect':'Deny','Principal':'*','Action':'elasticfilesystem:*','Resource':'*','Condition':{'Bool':{'aws:SecureTransport':'false'}}}]}), retain=True)
    for i in (0,1):
        add(f'FilesMount{i}', 'EFS::MountTarget', dict(FileSystemId=ref('Files'), SubnetId=ref(f'Private{i}'), SecurityGroups=[ref('FilesGroup')]))
    add('Uploads', 'EFS::AccessPoint', dict(FileSystemId=ref('Files'), PosixUser={'Uid':'10001','Gid':'10001'}, RootDirectory={'Path':'/uploads','CreationInfo':{'OwnerUid':'10001','OwnerGid':'10001','Permissions':'0750'}}), retain=True)
    add('Images', 'ECR::Repository', dict(ImageTagMutability='IMMUTABLE', ImageScanningConfiguration={'ScanOnPush':True}, EncryptionConfiguration={'EncryptionType':'AES256'}, EmptyOnDelete=False), retain=True)
    add('Logs', 'Logs::LogGroup', dict(RetentionInDays=30), retain=True)
    assume={'Version':'2012-10-17','Statement':[{'Effect':'Allow','Principal':{'Service':'ecs-tasks.amazonaws.com'},'Action':'sts:AssumeRole'}]}
    add('ExecutionRole', 'IAM::Role', dict(AssumeRolePolicyDocument=assume, Policies=[{'PolicyName':'ImageAndLogs','PolicyDocument':{'Version':'2012-10-17','Statement':[
        {'Effect':'Allow','Action':'ecr:GetAuthorizationToken','Resource':'*'},
        {'Effect':'Allow','Action':['ecr:BatchCheckLayerAvailability','ecr:GetDownloadUrlForLayer','ecr:BatchGetImage'],'Resource':attr('Images','Arn')},
        {'Effect':'Allow','Action':['logs:CreateLogStream','logs:PutLogEvents'],'Resource':attr('Logs','Arn')}
    ]}}]))
    add('AppRole', 'IAM::Role', dict(AssumeRolePolicyDocument=assume, Policies=[{'PolicyName':'SettingsAndUploads','PolicyDocument':{'Version':'2012-10-17','Statement':[
        {'Effect':'Allow','Action':'secretsmanager:GetSecretValue','Resource':ref('SettingsSecretArn')},
        {'Effect':'Allow','Action':['elasticfilesystem:ClientMount','elasticfilesystem:ClientWrite'],'Resource':attr('Files','Arn'),'Condition':{'StringEquals':{'elasticfilesystem:AccessPointArn':attr('Uploads','Arn')}}}
    ]}}]))
    add('Cluster', 'ECS::Cluster', dict(ClusterSettings=[{'Name':'containerInsights','Value':'disabled'}]))
    add('Task', 'ECS::TaskDefinition', dict(Cpu='256', Memory='512', NetworkMode='awsvpc', RequiresCompatibilities=['FARGATE'], ExecutionRoleArn=attr('ExecutionRole','Arn'), TaskRoleArn=attr('AppRole','Arn'), RuntimePlatform={'CpuArchitecture':'X86_64','OperatingSystemFamily':'LINUX'}, Volumes=[{'Name':'uploads','EFSVolumeConfiguration':{'FilesystemId':ref('Files'),'TransitEncryption':'ENABLED','AuthorizationConfig':{'AccessPointId':ref('Uploads'),'IAM':'ENABLED'}}}], ContainerDefinitions=[dict(Name='zova', Essential=True, Image=ref('ImageDigestUri'), User='10001:10001', Command=['python','scripts/aws_beta_entrypoint.py'], StopTimeout=120, PortMappings=[{'ContainerPort':10000}], MountPoints=[{'SourceVolume':'uploads','ContainerPath':'/app/uploads','ReadOnly':False}], Environment=[{'Name':k,'Value':v} for k,v in {
        'ZOVA_AWS_SETTINGS_SECRET_ARN':ref('SettingsSecretArn'), 'AWS_DEFAULT_REGION':ref('AWS::Region'),
        'PUBLIC_BASE_URL':'https://zova-social.com', 'PORT':'10000','UPLOAD_DIR':'/app/uploads',
        'ZOVA_SCHEDULER_MODE':ref('SchedulerMode'),'ZOVA_SCHEMA_MODE':'verify','ZOVA_WEB_REPLICAS':'1',
        'STRIPE_MODE':'test','STRIPE_LIVE_CHECKOUT_ENABLED':'false','REQUIRE_SUBSCRIPTION':'false','PLAN_LIMITS_ENABLED':'false'
    }.items()], LogConfiguration={'LogDriver':'awslogs','Options':{'awslogs-group':ref('Logs'),'awslogs-region':ref('AWS::Region'),'awslogs-stream-prefix':'web'}})]))
    add('Balancer', 'ElasticLoadBalancingV2::LoadBalancer', dict(Type='application', Scheme='internet-facing', Subnets=[ref('Public0'),ref('Public1')], SecurityGroups=[ref('FrontGroup')], LoadBalancerAttributes=[{'Key':'routing.http.drop_invalid_header_fields.enabled','Value':'true'},{'Key':'deletion_protection.enabled','Value':'true'}]))
    add('Targets', 'ElasticLoadBalancingV2::TargetGroup', dict(Port=10000, Protocol='HTTP', TargetType='ip', VpcId=ref('Network'), HealthCheckPath='/health', Matcher={'HttpCode':'200'}, TargetGroupAttributes=[{'Key':'deregistration_delay.timeout_seconds','Value':'120'}]))
    add('Https', 'ElasticLoadBalancingV2::Listener', dict(LoadBalancerArn=ref('Balancer'), Port=443, Protocol='HTTPS', SslPolicy='ELBSecurityPolicy-TLS13-1-2-2021-06', Certificates=[{'CertificateArn':ref('CertificateArn')}], DefaultActions=[{'Type':'forward','TargetGroupArn':ref('Targets')}]))
    add('Http', 'ElasticLoadBalancingV2::Listener', dict(LoadBalancerArn=ref('Balancer'), Port=80, Protocol='HTTP', DefaultActions=[{'Type':'redirect','RedirectConfig':{'Protocol':'HTTPS','Port':'443','StatusCode':'HTTP_301'}}]))
    add('Service', 'ECS::Service', dict(Cluster=ref('Cluster'), LaunchType='FARGATE', PlatformVersion='1.4.0', TaskDefinition=ref('Task'), DesiredCount=ref('DesiredCount'), EnableExecuteCommand=False, HealthCheckGracePeriodSeconds=90, DeploymentConfiguration={'MinimumHealthyPercent':0,'MaximumPercent':100,'DeploymentCircuitBreaker':{'Enable':True,'Rollback':True}}, NetworkConfiguration={'AwsvpcConfiguration':{'AssignPublicIp':'ENABLED','Subnets':[ref('Public0'),ref('Public1')],'SecurityGroups':[ref('AppGroup')]}}, LoadBalancers=[{'ContainerName':'zova','ContainerPort':10000,'TargetGroupArn':ref('Targets')}]), DependsOn=['Https','FilesMount0','FilesMount1'])
    add('Budget', 'Budgets::Budget', dict(Budget={'BudgetName':sub('${AWS::StackName}-monthly'),'BudgetType':'COST','TimeUnit':'MONTHLY','BudgetLimit':{'Amount':ref('MonthlyBudgetUsd'),'Unit':'USD'}}, NotificationsWithSubscribers=[{'Notification':{'NotificationType':'ACTUAL','ComparisonOperator':'GREATER_THAN','Threshold':80,'ThresholdType':'PERCENTAGE'},'Subscribers':[{'SubscriptionType':'EMAIL','Address':'david@zova-social.com'}]}]))
    return {'AWSTemplateFormatVersion':'2010-09-09','Description':'Zova beta candidate. No DNS changes. Zero tasks until verified restore and cutover. Budget alerts do not cap spend.',
        'Parameters':{
            'CertificateArn':{'Type':'String','AllowedPattern':'arn:aws:acm:.*:certificate/.*','Description':'Existing validated certificate for zova-social.com in this region'},
            'SettingsSecretArn':{'Type':'String','AllowedPattern':'arn:aws:secretsmanager:.*:secret:.*','Description':'Existing same-region AWS-managed-key secret with preserved application settings and restored runtime DB URL'},
            'ImageDigestUri':{'Type':'String','AllowedPattern':'.*\\.dkr\\.ecr\\..*\\.amazonaws\\.com/.*@sha256:[a-f0-9]{64}','Description':'Immutable reviewed image in the repository created by this stack; update after build'},
            'PostgresVersion':{'Type':'String','AllowedPattern':'17\\.[0-9]+','Description':'Select an available supported PostgreSQL 17 minor version after source dump compatibility check'},
            'DesiredCount':{'Type':'Number','Default':0,'AllowedValues':[0,1]},
            'SchedulerMode':{'Type':'String','Default':'disabled','AllowedValues':['disabled','embedded']},
            'MonthlyBudgetUsd':{'Type':'Number','Default':75,'MinValue':1}},
        'Rules':{'LondonOnly':{'Assertions':[{'Assert':{'Fn::Equals':[ref('AWS::Region'),'eu-west-2']},'AssertDescription':'This reviewed template and database trust store require London.'}]}},
        'Resources':r,'Outputs':{'LoadBalancerHost':{'Value':attr('Balancer','DNSName')},'RepositoryUri':{'Value':attr('Images','RepositoryUri')},'DatabaseHost':{'Value':attr('Database','Endpoint.Address')},'DatabaseAdminSecretArn':{'Value':attr('Database','MasterUserSecret.SecretArn')},'UploadsFileSystemId':{'Value':ref('Files')},'UploadsAccessPointId':{'Value':ref('Uploads')},'ClusterArn':{'Value':attr('Cluster','Arn')},'ApplicationService':{'Value':ref('Service')}}}


if __name__ == '__main__':
    Path(__file__).with_name('beta.template.json').write_text(json.dumps(template(), indent=2)+'\n',encoding='utf-8')
