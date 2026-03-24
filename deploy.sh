#!/bin/bash
# deploy.sh
set -e

IMAGE_TAG=${1:-latest}
SERVICE_NAME=${2:-all}

if [ -z "$INSTANCE_ID" ] || [ -z "$REGION" ]; then
    echo "Error: INSTANCE_ID and REGION environment variables must be set."
    exit 1
fi

echo "Preparing deployment payload for [$SERVICE_NAME] ($IMAGE_TAG)..."

# Assets
COMPOSE_B64=$(base64 -w 0 docker-compose.production.yml)
REGISTRY_B64=$(base64 -w 0 machine_learning/model_registry.json)
MONITOR_B64=$(base64 -w 0 monitor_docker.ps1)
SERVICE_B64=$(base64 -w 0 mc-monitor.service)

# Build the payload shell script by replacing placeholders
# We use '|' as sed separator because paths/base64 might contain '/'
PAYLOAD=$(sed \
    -e "s|__IMAGE_TAG__|$IMAGE_TAG|g" \
    -e "s|__SERVICE_NAME__|$SERVICE_NAME|g" \
    -e "s|__REGION__|$REGION|g" \
    -e "s|__COMPOSE_B64__|$COMPOSE_B64|g" \
    -e "s|__REGISTRY_B64__|$REGISTRY_B64|g" \
    -e "s|__MONITOR_B64__|$MONITOR_B64|g" \
    -e "s|__SERVICE_B64__|$SERVICE_B64|g" \
    remote_deploy.sh.template)

# Encode the entire script to avoid any SSM shell escaping issues
B64_PAYLOAD=$(echo "$PAYLOAD" | base64 -w 0)

echo "Sending execution command to instance $INSTANCE_ID..."

COMMAND_ID=$(aws ssm send-command \
    --region "$REGION" \
    --instance-ids "$INSTANCE_ID" \
    --document-name "AWS-RunShellScript" \
    --parameters "commands=[echo $B64_PAYLOAD | base64 -d | bash]" \
    --comment "Deploying $SERVICE_NAME with tag $IMAGE_TAG" \
    --query "Command.CommandId" --output text)

echo "Command sent! ID: $COMMAND_ID"
echo "Monitoring deployment progress (this may take a few minutes)..."

# Poll status
while true; do
    # Get command status
    STATUS=$(aws ssm get-command-invocation \
        --command-id "$COMMAND_ID" \
        --instance-id "$INSTANCE_ID" \
        --region "$REGION" \
        --query "Status" --output text 2>/dev/null || echo "Pending")

    case "$STATUS" in
        "Success")
            echo -e "\nDeployment SUCCESSFUL!"
            echo "--- EC2 LOGS ---"
            aws ssm get-command-invocation \
                --command-id "$COMMAND_ID" \
                --instance-id "$INSTANCE_ID" \
                --region "$REGION" \
                --query "StandardOutputContent" --output text
            exit 0
            ;;
        "Failed"|"TimedOut"|"Cancelled")
            echo -e "\nDeployment FAILED! (Status: $STATUS)"
            echo "--- ERROR LOGS ---"
            aws ssm get-command-invocation \
                --command-id "$COMMAND_ID" \
                --instance-id "$INSTANCE_ID" \
                --region "$REGION" \
                --query "StandardErrorContent" --output text
            echo "--- OUTPUT LOGS ---"
            aws ssm get-command-invocation \
                --command-id "$COMMAND_ID" \
                --instance-id "$INSTANCE_ID" \
                --region "$REGION" \
                --query "StandardOutputContent" --output text
            exit 1
            ;;
        *)
            echo -n "."
            sleep 10
            ;;
    esac
done
