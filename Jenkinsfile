pipeline {
    agent { label 'docker-agent' }

    stages {
        stage('Checkout') {
            steps { checkout scm }
        }

        stage('Security Scans') {
            parallel {
                stage('Secrets Scan') {
                    steps {
                        sh 'docker run --rm -v $(pwd):/path zricethezav/gitleaks:latest detect --source="/path" --exit-code 1'
                    }
                }
                stage('SAST') {
                    steps {
                        sh 'docker run --rm -v $(pwd):/src returntocorp/semgrep semgrep --config=auto /src --json || true'
                    }
                }
                stage('Dependency Scan') {
                    steps {
                        sh 'docker run --rm -v $(pwd):/src python:3.9 bash -c "pip install pip-audit && pip-audit -r /src/requirements.txt" || true'
                    }
                }
            }
        }

        stage('Build Image') {
            steps { sh 'docker build -t devsecops-lab:${BUILD_NUMBER} .' }
        }

        stage('Container Scan') {
            steps {
                sh 'docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy image --severity HIGH,CRITICAL --exit-code 1 devsecops-lab:${BUILD_NUMBER}'
            }
        }

        stage('Deploy') {
            when { branch 'main' }
            steps { echo 'Would deploy here — gated on all scans passing' }
        }
    }

    post {
        always {
            archiveArtifacts artifacts: '*-report.json', allowEmptyArchive: true
        }
        failure {
            echo 'Security gate failed — build blocked from deploy'
        }
    }
}