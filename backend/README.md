# AvendroSystem - Lending Management System

A comprehensive lending management system built with Django, designed to streamline loan operations and financial management for lending institutions.

## 🚀 Features

- **User Management**: Secure authentication and authorization system
- **Loan Management**: Complete loan lifecycle management
- **Payment Processing**: Track payments, installments, and dues
- **Customer Management**: Comprehensive customer profiles and history
- **Reporting & Analytics**: Financial reports and loan analytics
- **Admin Dashboard**: Administrative interface for system management

## 🛠️ Tech Stack

- **Backend**: Python Django 5.1+
- **Frontend**: HTML, CSS, JavaScript, Tailwind CSS
- **Database**: PostgreSQL (Production) / SQLite (Development)
- **Authentication**: JWT tokens with Django REST Framework
- **API**: Django REST Framework for API endpoints

## 📋 Requirements

- Python 3.13+
- Django 5.1+
- PostgreSQL (for production)
- Node.js (for frontend dependencies)

## 🔧 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/Yirmeyahuu/LendingSystem.git
cd AvendroSystem
```

### 2. Set up Virtual Environment

```bash
# Create virtual environment
python -m venv virt

# Activate virtual environment
# On macOS/Linux:
source virt/bin/activate
# On Windows:
virt\Scripts\activate
```

### 3. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 4. Environment Configuration

Create a `.env` file in the backend directory:

```env
SECRET_KEY=your-secret-key-here
DEBUG=True
DATABASE_URL=postgresql://username:password@localhost:5432/avendro_db
ALLOWED_HOSTS=localhost,127.0.0.1
```

### 5. Database Setup

```bash
# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Load initial data (if available)
python manage.py loaddata fixtures/initial_data.json
```

### 6. Run the Development Server

```bash
python manage.py runserver
```

The application will be available at `http://127.0.0.1:8000`

## 📁 Project Structure

```
AvendroSystem/
├── backend/                 # Django backend application
│   ├── Avendro/            # Main Django project
│   │   ├── __init__.py
│   │   ├── settings.py     # Django settings
│   │   ├── urls.py         # URL routing
│   │   ├── wsgi.py
│   │   └── asgi.py
│   ├── manage.py           # Django management script
│   └── requirements.txt    # Python dependencies
├── virt/                   # Virtual environment
├── .gitignore             # Git ignore rules
└── README.md              # Project documentation
```

## 🔑 Key Dependencies

- **Django**: Web framework
- **Django REST Framework**: API development
- **django-cors-headers**: CORS handling
- **djangorestframework-simplejwt**: JWT authentication
- **psycopg2-binary**: PostgreSQL adapter
- **python-dotenv**: Environment variables
- **Pillow**: Image processing

## 🌐 API Endpoints

Once the application is running, the following endpoints will be available:

- `/admin/` - Django admin interface
- `/api/auth/` - Authentication endpoints
- `/api/loans/` - Loan management endpoints
- `/api/customers/` - Customer management endpoints
- `/api/payments/` - Payment processing endpoints

## 🗄️ Database Configuration

### Development (SQLite)
The project is configured to use SQLite for development by default.

### Production (PostgreSQL)
For production, update your `.env` file with PostgreSQL credentials:

```env
DATABASE_URL=postgresql://username:password@localhost:5432/avendro_db
```

## 🧪 Testing

Run the test suite:

```bash
python manage.py test
```

## 📊 Development Workflow

1. **Create a new branch** for features/fixes
2. **Write tests** for new functionality
3. **Update documentation** as needed
4. **Submit pull request** for review

## 🚀 Deployment

### Production Checklist

- [ ] Set `DEBUG=False` in production
- [ ] Configure PostgreSQL database
- [ ] Set up static file serving
- [ ] Configure ALLOWED_HOSTS
- [ ] Set up proper logging
- [ ] Configure HTTPS
- [ ] Set up backup strategy

### Environment Variables

Key environment variables for production:

```env
SECRET_KEY=your-production-secret-key
DEBUG=False
DATABASE_URL=postgresql://user:pass@localhost:5432/production_db
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
STATIC_ROOT=/path/to/static/files
MEDIA_ROOT=/path/to/media/files
```

## 📈 Future Enhancements

- [ ] Mobile application (React Native/Flutter)
- [ ] Advanced analytics dashboard
- [ ] Automated loan approval system
- [ ] Integration with payment gateways
- [ ] Multi-currency support
- [ ] Document management system
- [ ] SMS/Email notifications
- [ ] Audit trail system

## 🤝 Contributing

1. Fork the project
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 👥 Team

- **Yirmeyahuu** - Project Owner & Lead Developer

## 📧 Support

For support and questions, please contact:
- Email: [your-email@example.com]
- GitHub Issues: [Project Issues](https://github.com/Yirmeyahuu/LendingSystem/issues)

## 🙏 Acknowledgments

- Django community for the excellent framework
- Contributors and testers
- Open source libraries that made this project possible

---

**Note**: This is a lending management system designed for educational and business purposes. Ensure compliance with local financial regulations when deploying in production.