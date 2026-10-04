group "default" {
  targets = ["web", "data-ingestion", "recognition", "scraper"]
}

target "web" {
  context = "."
  tags = ["pokex-web"]
  dockerfile = "apps/web/Dockerfile"
}

target "data-ingestion" {
  context = "./services/data-ingestion"
  tags = ["pokex-data-ingestion"]
  dockerfile = "Dockerfile"
  platforms = ["linux/amd64", "linux/arm64"]
}

target "recognition" {
  context = "./services/recognition"
  tags = ["pokex-recognition"]
  dockerfile = "Dockerfile"
  platforms = ["linux/amd64"]
}

target "scraper" {
  context = "./services/scraper"
  tags = ["pokex-scraper"]
  dockerfile = "Dockerfile"
  platforms = ["linux/amd64", "linux/arm64"]
}