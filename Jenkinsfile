pipeline {
    agent { label 'docker-agent' }

    environment {
        APP_ENV = 'lab'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        stage('Security Scan') {
            steps {
                sh 'docker run --rm -v $(pwd):/path zricethezav/gitleaks:latest detect --source="/path" --exit-code 1'          
            }
        }
        stage('Build') {
            steps {
                sh 'echo "Building in $APP_ENV..."'
            }
        }
        stage('Test') {
            steps {
                sh 'echo "Running tests..."'
            }
        }
        stage('Parallel Checks') {
            parallel {
                stage('Lint') {
                    steps { sh 'echo linting...' }
                }
                stage('Security Scan Placeholder') {
                    steps { sh 'echo scanning...' }
                }
            }
        }
        stage('Deploy') {
            when {
                branch 'main'
            }
            steps {
                sh 'echo deploying to lab environment'
            }
        }
    }

    post {
        always {
            archiveArtifacts artifacts: 'gitleaks-report.json', allowEmptyArchive: true 
        }
    }
}
