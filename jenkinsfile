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
        success {
            echo 'Pipeline succeeded'
        }
        failure {
            echo 'Pipeline failed — would alert here'
        }
        always {
            echo 'Cleaning workspace'
            cleanWs()
        }
    }
}
