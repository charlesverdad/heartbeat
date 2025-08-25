variable "location" {
  description = "Azure region for resources"
  type        = string
  default     = "australiaeast"
}

variable "environment" {
  description = "Environment name (dev, prod, etc.)"
  type        = string
  default     = "prod"
}

variable "vm_name" {
  description = "Name of the virtual machine"
  type        = string
  default     = "vm1"
}

variable "vm_size" {
  description = "Size of the virtual machine"
  type        = string
  default     = "Standard_B1ms"
}

variable "data_disk_size" {
  description = "Size of the data disk in GB"
  type        = number
  default     = 32
}

variable "vnet_address_space" {
  description = "Address space for the virtual network"
  type        = string
  default     = "10.42.0.0/16"
}

variable "subnet_address_space" {
  description = "Address space for the subnet"
  type        = string
  default     = "10.42.1.0/24"
}

variable "admin_username" {
  description = "Administrator username for the VM"
  type        = string
  default     = "user"
}

variable "git_repo_url" {
  description = "Git repository URL to clone"
  type        = string
  default     = "https://github.com/charlesverdad/heartbeat"
}

variable "tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default = {
    Project     = "vm1-prod"
    ManagedBy   = "terraform"
    Environment = "prod"
  }
}
