variable "account_id" {
  type = string
}

variable "dns_records" {
  type    = list(object({ identifier = string, name = string, type = string, ttl = number, value = string, proxied = bool, priority = number }))
  default = []
}

variable "plan" {
  type    = string
  default = null
}

variable "rulesets" {
  type    = list(object({ identifier = string, name = string, kind = string, phase = string, description = string, rules = list(object({ action = string, expression = string, description = string, enabled = bool, ref = string, action_parameters = map(any) })) }))
  default = []
}

variable "type" {
  type    = string
  default = null
}

variable "zone" {
  type = string
}
