from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework import status
from django.urls import reverse
from .models import EmailVerificationCode
import datetime
from django.utils import timezone

class EmailVerificationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.send_code_url = reverse('send_verification_code')
        self.verify_code_url = reverse('verify_code')
        self.valid_email = 'test@example.com'
        self.invalid_email = 'invalid_email'
        
    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_send_verification_code_success(self):
        """Test successfully sending a verification code"""
        data = {'email': self.valid_email}
        response = self.client.post(self.send_code_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(EmailVerificationCode.objects.filter(email=self.valid_email).exists())
        
    def test_send_verification_code_invalid_email(self):
        """Test sending code with invalid email format"""
        data = {'email': self.invalid_email}
        response = self.client.post(self.send_code_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data['details'])
        
    def test_verify_code_success(self):
        """Test successfully verifying a code"""
        # First create a valid code
        code = '123456'
        EmailVerificationCode.objects.create(
            email=self.valid_email,
            code=code,
            created_at=timezone.now(),
            expires_at=timezone.now() + datetime.timedelta(minutes=5)
        )
        
        data = {'email': self.valid_email, 'code': code}
        response = self.client.post(self.verify_code_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['success'], 'Email successfully verified')
        
    def test_verify_code_expired(self):
        """Test verifying an expired code"""
        code = '123456'
        EmailVerificationCode.objects.create(
            email=self.valid_email,
            code=code,
            created_at=timezone.now() - datetime.timedelta(minutes=10),
            expires_at=timezone.now() - datetime.timedelta(minutes=5)
        )
        
        data = {'email': self.valid_email, 'code': code}
        response = self.client.post(self.verify_code_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'Verification code has expired')
        
    def test_verify_code_invalid(self):
        """Test verifying with wrong code"""
        EmailVerificationCode.objects.create(
            email=self.valid_email,
            code='123456',
            created_at=timezone.now(),
            expires_at=timezone.now() + datetime.timedelta(minutes=5)
        )
        
        data = {'email': self.valid_email, 'code': 'wrongcode'}
        response = self.client.post(self.verify_code_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'Invalid verification code')
        
    def test_verify_code_no_request(self):
        """Test verifying when no verification request exists"""
        data = {'email': self.valid_email, 'code': '123456'}
        response = self.client.post(self.verify_code_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data['error'], 'No verification request found for this email')
