{{/* Selector labels: identical to the bitnami chart's (a Deployment's selector is immutable). */}}
{{- define "minio.selectorLabels" -}}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/name: minio
{{- end }}

{{- define "minio.labels" -}}
{{ include "minio.selectorLabels" . }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/version: {{ .Values.image.tag | quote }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version }}
{{- end }}

{{- define "minio.image" -}}
{{- if .Values.image.digest -}}
{{ .Values.image.repository }}@{{ .Values.image.digest }}
{{- else -}}
{{ .Values.image.repository }}:{{ required "image.tag or image.digest is required" .Values.image.tag }}
{{- end -}}
{{- end }}
