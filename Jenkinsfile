// =============================================================================
// tasks-api : DevSecOps pipeline (Multibranch, Docker-out-of-Docker agent)
//
// Branch model:   feature/* -> develop -> release/x.y -> main
//   PR / feature  : build, test, scan            (no push, no deploy)
//   develop       : + push to Harbor, deploy dev
//   release/*     : + stricter gate, deploy staging, DAST
//   main          : + manual approval, deploy prod
//
// Rule for every `docker run -v` below: the host daemon resolves the path, so
// $PWD must exist on the host. That is why the agent mounts its workdir at the
// SAME path on both sides.
// =============================================================================

pipeline {
  agent { label 'docker-agent-1' }

  parameters {
    booleanParam(name: 'DEPLOY', defaultValue: false,
      description: 'Deploy to the cluster for this branch (needs kubeconfig credentials)')
    booleanParam(name: 'WAIT_FOR_QUALITY_GATE', defaultValue: false,
      description: 'Block on the SonarQube Quality Gate (needs the Sonar -> Jenkins webhook)')
  }

  options {
    timestamps()
    timeout(time: 90, unit: 'MINUTES')
    disableConcurrentBuilds()
    buildDiscarder(logRotator(numToKeepStr: '20', artifactNumToKeepStr: '10'))
  }

  environment {
    APP            = 'tasks-api'
    REGISTRY       = 'localhost:8081'          // pushes go through the HOST daemon
    HARBOR_PROJECT = 'myapp'
    DOCKER_NET     = 'jenkins-lab'
    TRIVY_SERVER   = 'http://trivy-server:4954'

    // Tool images in ONE place. Pin tags/digests when you harden this.
    // Trivy client and server MUST be the same version.
    GITLEAKS_IMG = 'zricethezav/gitleaks:latest'
    SEMGREP_IMG  = 'semgrep/semgrep:latest'
    SONAR_IMG    = 'sonarsource/sonar-scanner-cli:latest'
    TRIVY_IMG    = 'aquasec/trivy:latest'
    ZAP_IMG      = 'zaproxy/zap-stable:latest'
  }

  stages {

    // -------------------------------------------------------------------------
    stage('Prepare') {
      steps {
        script {
          env.GIT_SHORT = sh(returnStdout: true, script: 'git rev-parse --short=7 HEAD').trim()
          env.IMAGE     = "${env.REGISTRY}/${env.HARBOR_PROJECT}/${env.APP}:${env.GIT_SHORT}"
          // Tiered gate: stricter on release/main
          env.TRIVY_SEVERITY = ((env.BRANCH_NAME ?: '') ==~ /main|release\/.+/) ? 'HIGH,CRITICAL' : 'CRITICAL'
        }
        sh '''
          mkdir -p reports
          # Guard 1: can a SIBLING container see this workspace? (DooD path check)
          docker run --rm -v "$PWD:/w" alpine test -f /w/requirements.txt
          # Guard 2: is the Trivy server reachable?
          curl -fsS "$TRIVY_SERVER/healthz"; echo
        '''
        echo "branch=${env.BRANCH_NAME} image=${env.IMAGE} trivy-severity=${env.TRIVY_SEVERITY}"
      }
    }

    // -------------------------------------------------------------------------
    stage('Secrets scan (Gitleaks)') {
      steps {
        sh '''
          docker run --rm --user "$(id -u):$(id -g)" -v "$PWD:/repo" "$GITLEAKS_IMG" \
            detect --source /repo --no-banner --redact \
            --report-path /repo/reports/gitleaks.json --exit-code 1
        '''
      }
    }

    // -------------------------------------------------------------------------
    stage('Lint & unit tests') {
      steps {
        sh '''
          python3 -m venv .venv
          . .venv/bin/activate
          pip install --quiet --disable-pip-version-check -r requirements-dev.txt
          flake8 app tests
          pytest
        '''
      }
      post {
        always { junit allowEmptyResults: true, testResults: 'junit.xml' }
      }
    }

    // -------------------------------------------------------------------------
    stage('SAST, SCA & config scans') {
      parallel {

        stage('Semgrep') {
          steps {
            sh '''
              docker run --rm --user "$(id -u):$(id -g)" -e HOME=/tmp \
                -v "$PWD:/src" -w /src "$SEMGREP_IMG" \
                semgrep scan --config p/python --config p/owasp-top-ten \
                --error --metrics=off --json-output=/src/reports/semgrep.json app
              # Guard: "0 findings" must not mean "0 files scanned"
              jq -e '.paths.scanned | length > 0' reports/semgrep.json > /dev/null
            '''
          }
        }

        stage('Bandit') {
          steps {
            sh '''
              . .venv/bin/activate
              rc=0
              bandit -r app -ll -f txt -o reports/bandit.txt || rc=$?
              cat reports/bandit.txt
              exit $rc
            '''
          }
        }

        stage('pip-audit') {
          steps {
            sh '. .venv/bin/activate && pip-audit -r requirements.txt'
          }
        }

        stage('Dockerfile & manifests (Trivy config)') {
          steps {
            sh '''
              docker run --rm --user "$(id -u):$(id -g)" -e TRIVY_CACHE_DIR=/tmp/trivy \
                -v "$PWD:/src" "$TRIVY_IMG" \
                config --severity HIGH,CRITICAL --exit-code 1 \
                --skip-dirs /src/.venv --skip-dirs /src/.git /src
            '''
          }
        }
      }
    }

    // -------------------------------------------------------------------------
    // Community Edition has ONE analysis per project (no branch support), so
    // only the long-lived branches write to it.
    stage('SonarQube analysis') {
      when { anyOf { branch 'develop'; branch 'main'; branch 'release/*' } }
      steps {
        withSonarQubeEnv('sonarqube') {
          sh '''
            docker run --rm --user "$(id -u):$(id -g)" --network "$DOCKER_NET" \
              -e SONAR_HOST_URL="$SONAR_HOST_URL" -e SONAR_TOKEN="$SONAR_AUTH_TOKEN" \
              -e SONAR_USER_HOME=/tmp/.sonar \
              -v "$PWD:/usr/src" "$SONAR_IMG" \
              -Dsonar.projectVersion="$GIT_SHORT"
          '''
        }
      }
    }

    stage('Quality Gate') {
      when {
        allOf {
          expression { params.WAIT_FOR_QUALITY_GATE }
          anyOf { branch 'develop'; branch 'main'; branch 'release/*' }
        }
      }
      steps {
        timeout(time: 5, unit: 'MINUTES') {
          waitForQualityGate abortPipeline: true
        }
      }
    }

    // -------------------------------------------------------------------------
    stage('Build image') {
      steps {
        sh '''
          docker build --pull \
            --label "org.opencontainers.image.revision=$GIT_COMMIT" \
            --label "org.opencontainers.image.version=$GIT_SHORT" \
            -t "$IMAGE" .
        '''
      }
    }

    // Scan BEFORE push: a vulnerable image never reaches the registry.
    stage('Image scan (Trivy)') {
      steps {
        sh '''
          # 1) full report for the audit trail (never fails)
          docker run --rm --network "$DOCKER_NET" \
            -v /var/run/docker.sock:/var/run/docker.sock \
            -v "$PWD/reports:/reports" "$TRIVY_IMG" \
            image --server "$TRIVY_SERVER" --format json \
            --output /reports/trivy-image.json "$IMAGE"

          # 2) the gate
          docker run --rm --network "$DOCKER_NET" \
            -v /var/run/docker.sock:/var/run/docker.sock "$TRIVY_IMG" \
            image --server "$TRIVY_SERVER" \
            --severity "$TRIVY_SEVERITY" --ignore-unfixed --exit-code 1 "$IMAGE"
        '''
      }
    }

    stage('Push to Harbor') {
      when {
        allOf {
          not { changeRequest() }
          anyOf { branch 'develop'; branch 'main'; branch 'release/*' }
        }
      }
      steps {
        withVault(vaultSecrets: [[
          path: 'secret/myapp/harbor', engineVersion: 2,
          secretValues: [
            [envVar: 'HARBOR_USER', vaultKey: 'username'],
            [envVar: 'HARBOR_PASS', vaultKey: 'password']
          ]
        ]]) {
          sh '''
            export DOCKER_CONFIG="$(mktemp -d)"      # login state never persists
            trap 'rm -rf "$DOCKER_CONFIG"' EXIT
            echo "$HARBOR_PASS" | docker login "$REGISTRY" -u "$HARBOR_USER" --password-stdin
            docker push "$IMAGE"
          '''
        }
      }
    }

    // -------------------------------------------------------------------------
    stage('Deploy dev') {
      when { allOf { branch 'develop'; expression { params.DEPLOY } } }
      steps { deployTo('dev') }
    }

    stage('Deploy staging') {
      when { allOf { branch 'release/*'; expression { params.DEPLOY } } }
      steps { deployTo('staging') }
    }

    // DAST against a throwaway container of the image we just built.
    stage('DAST (OWASP ZAP baseline)') {
      when { branch 'release/*' }
      steps {
        sh '''
          TARGET="zap-target-${BUILD_NUMBER}"
          trap 'docker rm -f "$TARGET" >/dev/null 2>&1 || true' EXIT
          docker run -d --name "$TARGET" --network "$DOCKER_NET" "$IMAGE"

          for i in $(seq 1 45); do
            [ "$(docker inspect -f '{{.State.Health.Status}}' "$TARGET")" = "healthy" ] && break
            sleep 2
          done
          [ "$(docker inspect -f '{{.State.Health.Status}}' "$TARGET")" = "healthy" ]

          mkdir -p reports/zap && chmod 777 reports/zap   # ZAP runs as another UID
          rc=0
          docker run --rm --network "$DOCKER_NET" -v "$PWD/reports/zap:/zap/wrk:rw" "$ZAP_IMG" \
            zap-baseline.py -t "http://$TARGET:8000" -r zap-report.html || rc=$?

          # ZAP exit codes: 0 pass, 1 FAIL alerts, 2 warnings only
          [ "$rc" -eq 0 ] || [ "$rc" -eq 2 ]
        '''
      }
    }

    stage('Approve production') {
      when { allOf { branch 'main'; expression { params.DEPLOY }; beforeInput true } }
      options { timeout(time: 30, unit: 'MINUTES') }
      input {
        message 'Promote this build to PRODUCTION?'
        ok 'Deploy'
        submitter 'release-managers'   // lab: change to your own Jenkins username
      }
      steps { echo "Approved. Promoting ${env.IMAGE}" }
    }

    stage('Deploy prod') {
      when { allOf { branch 'main'; expression { params.DEPLOY } } }
      steps { deployTo('prod') }
    }
  }

  post {
    always {
      archiveArtifacts artifacts: 'reports/**', allowEmptyArchive: true
      sh 'docker rmi "$IMAGE" >/dev/null 2>&1 || true'
      cleanWs(notFailBuild: true)
    }
    failure { echo "FAILED: ${env.JOB_NAME} #${env.BUILD_NUMBER} (read the first red stage)" }
  }
}

// Substitutes the image at deploy time; the manifests in Git are never edited.
def deployTo(String targetEnv) {
  withCredentials([file(credentialsId: "kubeconfig-${targetEnv}", variable: 'KUBECONFIG')]) {
    sh """
      sed "s|IMAGE_PLACEHOLDER|${env.IMAGE}|" infra/${targetEnv}/deployment.yaml | kubectl apply -f -
      kubectl -n tasks-api-${targetEnv} rollout status deployment/tasks-api --timeout=120s
    """
  }
}
