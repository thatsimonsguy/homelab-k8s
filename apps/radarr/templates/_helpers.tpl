{{- define "radarr.fullname" -}}
{{ .Release.Name }}
{{- end }}

{{- define "radarr.labels" -}}
app: {{ .Release.Name }}
chart: {{ .Chart.Name }}-{{ .Chart.Version }}
release: {{ .Release.Name }}
heritage: {{ .Release.Service }}
{{- end }}

{{- define "radarr.selectorLabels" -}}
app: {{ .Release.Name }}
{{- end }}