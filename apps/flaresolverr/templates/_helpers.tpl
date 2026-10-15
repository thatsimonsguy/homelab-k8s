{{- define "flaresolverr.fullname" -}}
{{ .Release.Name }}
{{- end }}

{{- define "flaresolverr.labels" -}}
app: {{ .Release.Name }}
chart: {{ .Chart.Name }}-{{ .Chart.Version }}
release: {{ .Release.Name }}
heritage: {{ .Release.Service }}
{{- end }}

{{- define "flaresolverr.selectorLabels" -}}
app: {{ .Release.Name }}
{{- end }}
