variable "account_id" {
  type = string
}

variable "dns_records" {
  type    = list(object({ identifier = string, name = string, ttl = number, type = string, content = string, data = map(any), priority = number, proxied = bool }))
  default = []
}

variable "name" {
  type = string
}

variable "plan" {
  type    = string
  default = null
}

variable "rulesets" {
  type    = list(object({ identifier = string, kind = string, name = string, phase = string, description = string, rules = list(object({ action = string, expression = string, action_parameters = map(any), description = string, enabled = bool, ref = string })) }))
  default = []
}

variable "type" {
  type    = string
  default = null
}
