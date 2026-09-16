{{- define "traceroute-site.name" -}}
{{ .Chart.Name }}
{{- end }}
{{- define "traceroute-site.fullname" -}}
{{ .Release.Name }}
{{- end }}
{{- define "traceroute-site.labels" -}}
app.kubernetes.io/name: {{ include "traceroute-site.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion }}
{{- end }}
