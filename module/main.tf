provider "cloudflare" {
  # API token will be read from CLOUDFLARE_API_TOKEN environment variable
}

resource "cloudflare_zone" "this" {
  account = {
    id = var.account_id
  }
  name = var.zone
  type = var.type
}

resource "cloudflare_zone_subscription" "this" {
  count   = var.plan != null ? 1 : 0
  zone_id = cloudflare_zone.this.id
  rate_plan = {
    id = var.plan
  }
}

resource "cloudflare_dns_record" "this" {
  for_each = {
    for record in var.dns_records : record.identifier => record
  }

  zone_id  = cloudflare_zone.this.id
  name     = each.value.name
  content  = each.value.value
  type     = each.value.type
  ttl      = each.value.ttl
  proxied  = each.value.proxied
  priority = each.value.priority
}

resource "cloudflare_ruleset" "this" {
  for_each = {
    for ruleset in var.rulesets : ruleset.identifier => ruleset
  }

  zone_id     = cloudflare_zone.this.id
  name        = each.value.name
  description = each.value.description
  kind        = each.value.kind
  phase       = each.value.phase
  rules       = each.value.rules
}
