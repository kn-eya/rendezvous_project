# Multi-Service Appointment Management System

## 📌 Description
This project is a web application built with **Django** that allows different types of users to authenticate and manage appointments based on their roles.

The platform supports multiple service categories such as **hairdressers, doctors, and other service providers**, along with clients and an administrator who manages the entire system.

## 👥 User Roles

### 🔐 Authentication
- User registration and login
- Role-based access control

### 🧑‍⚕️ Service Provider (Hairdresser, Doctor, etc.)
- Select a service category
- View and manage appointments
- Receive notifications when a client books or updates an appointment

### 👤 Client
- Register and authenticate
- Choose a service category
- Book appointments
- Receive notifications about appointment status

### 🛡️ Admin
- Manage users (clients and service providers)
- Create, update, and delete service categories
- Manage appointments
- Control the entire application via the admin dashboard

## 🔔 Notifications
- Clients receive notifications for appointment confirmation or changes
- Service providers receive notifications for new or updated appointments

## 🛠️ Technologies Used
- Python
- Django
- HTML
- CSS
- Django Templates
- SQLite

## ⚙️ Installation

```bash
git clone https://github.com/kn-eya/rendezvous_project.git
cd rendezvous_project
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
