output "public_ip" {
  description = "Elastic IP of the monitoring EC2 instance"
  value       = aws_eip.monitoring.public_ip
}

output "pushgateway_url" {
  description = "URL that Lambda and SageMaker push metrics to"
  value       = "http://${aws_eip.monitoring.public_ip}:9091"
}

output "grafana_url" {
  description = "Grafana UI"
  value       = "http://${aws_eip.monitoring.public_ip}:3000"
}

output "prometheus_url" {
  description = "Prometheus UI"
  value       = "http://${aws_eip.monitoring.public_ip}:9090"
}

output "mlflow_url" {
  description = "MLflow tracking server"
  value       = "http://${aws_eip.monitoring.public_ip}:5000"
}
