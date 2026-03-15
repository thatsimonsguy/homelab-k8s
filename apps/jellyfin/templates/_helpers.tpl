{{- define "jellyfin.fullname" -}}
{{ .Release.Name }}
{{- end }}

{{- define "jellyfin.labels" -}}
app: {{ .Release.Name }}
chart: {{ .Chart.Name }}-{{ .Chart.Version }}
release: {{ .Release.Name }}
heritage: {{ .Release.Service }}
{{- end }}

{{- define "jellyfin.selectorLabels" -}}
app: {{ .Release.Name }}
{{- end }}
