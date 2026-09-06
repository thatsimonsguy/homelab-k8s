{{- define "aggsys.name" -}}
{{ .Chart.Name }}
{{- end }}

{{- define "aggsys.labels" -}}
app.kubernetes.io/name: {{ include "aggsys.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion }}
{{- end }}
