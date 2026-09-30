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
}

target "recognition" {
  context = "./services/recognition"
  tags = ["pokex-recognition"]
  dockerfile = "Dockerfile"
}

target "scraper" {
  context = "./services/scraper"
  tags = ["pokex-scraper"]
  dockerfile = "Dockerfile"
}