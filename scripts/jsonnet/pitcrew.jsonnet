local name = std.extVar('DRIVER_NAME_DASHED');
local name_topic = std.extVar('DRIVER_NAME');

{
  "apiVersion": "apps/v1",
  "kind": "Deployment",
  "metadata": {
    "name": "pitcrew-"+name,
    "labels": {
      "pitcrew.b4mad.racing/crewchiefname": name
    }
  },
  "spec": {
    "replicas": 1,
    "revisionHistoryLimit": 4,
    "selector": {
      "matchLabels": {
        "pitcrew.b4mad.racing/crewchiefname": name
      }
    },
    "strategy": {
      "type": "Recreate"
    },
    "template": {
      "metadata": {
        "labels": {
          "pitcrew.b4mad.racing/crewchiefname": name
        }
      },
      "spec": {
        "containers": [
          {
            "env": [
              {
                "name": "CREWCHIEF_USERNAME",
                "value": name_topic
              }
            ],
            "image": "quay.io/b4mad/pitcrew:latest",
            "name": "pitcrew",
            "resources": {
              "limits": {
                "memory": "64Mi",
                "cpu": "500m"
              }
            },
            "ports": [
              {
                "name": "dash",
                "containerPort": 8050,
                "protocol": "TCP"
              }
            ]
          }
        ],
        "restartPolicy": "Always"
      }
    }
  }
}
{
  "apiVersion": "v1",
  "kind": "Service",
  "metadata": {
    "name": "pitcrew-"+name,
    "labels": {
      "pitcrew.b4mad.racing/crewchiefname": name
    }
  },
  "spec": {
    "ports": [
      {
        "protocol": "TCP",
        "port": 80,
        "targetPort": 8050
      }
    ],
    "type": "ClusterIP",
    "selector": {
      "pitcrew.b4mad.racing/crewchiefname": name
    }
  }
}
{
  "apiVersion": "route.openshift.io/v1",
  "kind": "Route",
  "metadata": {
    "labels": {
      "pitcrew.b4mad.racing/crewchiefname": name
    },
    "name": "pitcrew-"+name,
    "annotations": {
      "kubernetes.io/tls-acme": "true"
    }
  },
  "spec": {
    "host": "pitcrew.b4mad.racing",
    "path": "/"+name,
    "tls": {
      "termination": "edge"
    },
    "to": {
      "name": "pitcrew-"+name
    }
  }
}
