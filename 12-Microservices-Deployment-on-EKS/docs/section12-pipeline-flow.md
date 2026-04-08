# Section 12 Pipeline And Resource Flow

이 문서는 `/home/AWS-EKS-Class-Master/12-Microservices-Deployment-on-EKS` 폴더에서 구성한 FastAPI + Uvicorn + vanilla HTML + AWS SES 애플리케이션의 절차, 파이프라인, AWS 리소스 사용 흐름을 정리합니다.

## Build And Deploy Flow

```mermaid
flowchart LR
    DEV[Developer updates<br/>section 12 source files]
    ZIP[Zip source folder<br/>12-Microservices-Deployment-on-EKS]
    S3[S3 source object<br/>ses-email-fullstack-pipeline bucket]
    PIPE[CodePipeline<br/>ses-email-fullstack-pipeline]
    BUILD[CodeBuild Build<br/>build-ses-email-fullstack]
    ECR[ECR<br/>ses-email-fullstack]
    ARTIFACT[Build artifact<br/>exported-vars.env + manifests]
    DEPLOY[CodeBuild Deploy<br/>deploy-ses-email-fullstack]
    EKS[EKS cluster<br/>eksdemo1]

    DEV --> ZIP --> S3 --> PIPE
    PIPE --> BUILD
    BUILD --> ECR
    BUILD --> ARTIFACT
    ARTIFACT --> DEPLOY
    DEPLOY --> EKS
```

## Runtime Resource Flow

```mermaid
flowchart LR
    USER[User browser]
    ALB[ALB Ingress]
    APP[FastAPI SES fullstack Pod]
    IRSA[IRSA service account<br/>ses-email-app-sa]
    IAM[IAM role<br/>eks-ses-send-role]
    SES[Amazon SES]
    NOTIF[Optional notif-deploy.yaml<br/>notification namespace]
    SEC[Secrets Manager via CSI]

    USER --> ALB --> APP
    APP --> IRSA --> IAM --> SES
    NOTIF --> SEC
```

## Resource Notes

- `CodePipeline`: `ses-email-fullstack-pipeline`
- `CodeBuild build project`: `build-ses-email-fullstack`
- `CodeBuild deploy project`: `deploy-ses-email-fullstack`
- `ECR repository`: `086015456585.dkr.ecr.ap-northeast-2.amazonaws.com/ses-email-fullstack`
- `EKS cluster`: `eksdemo1`
- `IRSA role`: `arn:aws:iam::086015456585:role/eks-ses-send-role`
- `kubectl assume role`: `arn:aws:iam::086015456585:role/EksCodeBuildKubectlRole`
- `S3 artifact bucket`: `ses-email-fullstack-pipeline-086015456585-ap-northeast-2`

## Manifest Execution Order

```mermaid
flowchart TD
    N1[01-namespace.yml]
    N2[02-serviceaccount.yml]
    N3[03-configmap.yml]
    N4[04-secret.yml]
    N5[05-fastapi-email-deployment.yml]
    N6[06-fastapi-email-clusterip-service.yml]
    N7[07-alb-ingress.yml]
    N8[notif-deploy.yaml]

    N1 --> N2 --> N3 --> N4 --> N5 --> N6 --> N7
    N7 --> N8
```

## Architecture Diagram

![Section 12 AWS Architecture](./section12-aws-architecture.svg)

## Icon Source

- AWS Architecture Icons package downloaded from the official AWS architecture icons page:
  `https://aws.amazon.com/architecture/icons/`
