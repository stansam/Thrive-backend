import pytest
from unittest.mock import patch, MagicMock
from app.services.notification import NotificationService
from app.models.notification import Notification
from app.models.user import User

@pytest.fixture
def notification_service():
    return NotificationService()

@pytest.fixture
def test_user_id(app, db):
    user = User(
        email="[email protected]",
        password_hash="hash",
        first_name="Test",
        last_name="User"
    )
    db.session.add(user)
    db.session.commit()
    return user.id

def test_create_notification(app, db, notification_service, test_user_id):
    with app.app_context():
        notification = notification_service._create_notification(
            user_id=str(test_user_id),
            notification_type="SYSTEM",
            title="Test Title",
            message="Test Message"
        )
        
        assert notification.id is not None
        assert notification.title == "Test Title"
        
        # Verify db persistence
        saved = Notification.query.get(notification.id)
        assert saved is not None
        assert saved.user_id == test_user_id

def test_send_booking_confirmation(app, notification_service, test_user_id):
    with app.app_context():
        user = User.query.get(test_user_id)
        mock_booking = MagicMock()
        mock_booking.id = "bk_123"
        mock_booking.booking_reference = "REF123"
        mock_booking.origin = "NYC"
        mock_booking.destination = "LON"
        mock_booking.total_price = "500.00"
        mock_booking.departure_date = None # simplified
        mock_booking.get_total_passengers.return_value = 1
        
        # Mock _send_email to avoid actual sending
        with patch.object(notification_service, '_send_email', return_value=True) as mock_send:
            notification_service.send_booking_confirmation(user, mock_booking)
            
            mock_send.assert_called_once()
            args, kwargs = mock_send.call_args
            assert kwargs['to_email'] == "[email protected]"
            assert "Booking Confirmation" in kwargs['subject']
            
            # Verify DB notification created
            notif = Notification.query.filter_by(booking_id="bk_123").first()
            assert notif is not None
            assert notif.title == "Booking Confirmed!"
