{{- define "sonarr.fullname" -}}
{{ .Release.Name }}
{{- end }}

{{- define "sonarr.labels" -}}
app: {{ .Release.Name }}
chart: {{ .Chart.Name }}-{{ .Chart.Version }}
release: {{ .Release.Name }}
heritage: {{ .Release.Service }}
{{- end }}

{{- define "sonarr.selectorLabels" -}}
app: {{ .Release.Name }}
{{- end }}