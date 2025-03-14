{{- define "jackett.fullname" -}}
{{ .Release.Name }}
{{- end }}

{{- define "jackett.labels" -}}
app: {{ .Release.Name }}
chart: {{ .Chart.Name }}-{{ .Chart.Version }}
release: {{ .Release.Name }}
heritage: {{ .Release.Service }}
{{- end }}

{{- define "jackett.selectorLabels" -}}
app: {{ .Release.Name }}
{{- end }}