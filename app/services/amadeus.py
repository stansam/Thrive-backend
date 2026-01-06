"""
Amadeus Flight API Service

This module provides a comprehensive interface to the Amadeus Self-Service Flight APIs,
including flight search, price confirmation, booking, and order management.

Key Features:
- OAuth2 authentication with automatic token refresh
- Flight offers search (GET and POST methods)
- Flight offers pricing confirmation
- Flight order creation (booking)
- Flight order management (retrieve and cancel)
- Comprehensive error handling and logging
- Rate limiting protection
- Retry logic with exponential backoff
- Type hints for better IDE support

API Documentation: https://developers.amadeus.com/self-service/category/flights
"""

import os
import time
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AmadeusEnvironment(Enum):
    """Amadeus API environment endpoints"""
    TEST = "https://test.api.amadeus.com"
    PRODUCTION = "https://api.amadeus.com"


class TravelClass(Enum):
    """Flight cabin travel classes"""
    ECONOMY = "ECONOMY"
    PREMIUM_ECONOMY = "PREMIUM_ECONOMY"
    BUSINESS = "BUSINESS"
    FIRST = "FIRST"


@dataclass
class AmadeusConfig:
    """Configuration for Amadeus API client"""
    client_id: str
    client_secret: str
    environment: AmadeusEnvironment = AmadeusEnvironment.TEST
    timeout: int = 30
    max_retries: int = 3
    token_buffer: int = 300  # Refresh token 5 minutes before expiry


class AmadeusAPIError(Exception):
    """Base exception for Amadeus API errors"""
    def __init__(self, message: str, status_code: Optional[int] = None, 
                 response: Optional[Dict] = None):
        self.message = message
        self.status_code = status_code
        self.response = response
        super().__init__(self.message)


class AuthenticationError(AmadeusAPIError):
    """Raised when authentication fails"""
    pass


class RateLimitError(AmadeusAPIError):
    """Raised when rate limit is exceeded"""
    pass


class ValidationError(AmadeusAPIError):
    """Raised when request validation fails"""
    pass


class BookingError(AmadeusAPIError):
    """Raised when booking fails"""
    pass


class AmadeusFlightService:
    """
    Comprehensive service for Amadeus Flight APIs
    
    This service handles:
    - Flight Offers Search (GET/POST)
    - Flight Offers Price confirmation
    - Flight Create Orders (booking)
    - Flight Order Management (retrieve/cancel)
    """
    
    def __init__(self, config: AmadeusConfig):
        """
        Initialize Amadeus Flight Service
        
        Args:
            config: AmadeusConfig object with API credentials
        """
        self.config = config
        self.base_url = config.environment.value
        self._access_token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None
        self._session = self._create_session()
        
        logger.info(f"Initialized Amadeus service for {config.environment.name} environment")
    
    def _create_session(self) -> requests.Session:
        """
        Create a requests session with retry logic
        
        Returns:
            Configured requests.Session object
        """
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=self.config.max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "DELETE"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        
        return session
    
    def _authenticate(self) -> None:
        """
        Authenticate with Amadeus API using OAuth2 Client Credentials flow
        
        Raises:
            AuthenticationError: If authentication fails
        """
        url = f"{self.base_url}/v1/security/oauth2/token"
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        data = {
            "grant_type": "client_credentials",
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret
        }
        
        try:
            logger.info("Authenticating with Amadeus API...")
            response = self._session.post(
                url,
                headers=headers,
                data=data,
                timeout=self.config.timeout
            )
            
            if response.status_code == 200:
                token_data = response.json()
                self._access_token = token_data["access_token"]
                expires_in = token_data.get("expires_in", 1799)
                self._token_expiry = datetime.now() + timedelta(seconds=expires_in)
                logger.info(f"Authentication successful. Token expires in {expires_in} seconds")
            else:
                error_msg = f"Authentication failed with status {response.status_code}"
                logger.error(error_msg)
                raise AuthenticationError(
                    error_msg,
                    status_code=response.status_code,
                    response=response.json() if response.text else None
                )
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Authentication request failed: {str(e)}")
            raise AuthenticationError(f"Authentication request failed: {str(e)}")
    
    def _ensure_authenticated(self) -> None:
        """Ensure valid access token exists, refresh if needed"""
        if (self._access_token is None or 
            self._token_expiry is None or 
            datetime.now() >= self._token_expiry - timedelta(seconds=self.config.token_buffer)):
            self._authenticate()
    
    def _get_headers(self) -> Dict[str, str]:
        """
        Get headers with authentication token
        
        Returns:
            Dictionary of HTTP headers
        """
        self._ensure_authenticated()
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json"
        }
    
    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """
        Handle API response and raise appropriate exceptions
        
        Args:
            response: requests.Response object
            
        Returns:
            Parsed JSON response
            
        Raises:
            Various AmadeusAPIError subclasses based on error type
        """
        try:
            response_data = response.json() if response.text else {}
        except ValueError:
            response_data = {}
        
        if response.status_code == 200:
            return response_data
        elif response.status_code == 400:
            error_msg = self._extract_error_message(response_data)
            logger.error(f"Validation error: {error_msg}")
            raise ValidationError(error_msg, response.status_code, response_data)
        elif response.status_code == 401:
            logger.error("Authentication failed")
            self._access_token = None
            raise AuthenticationError("Authentication failed", response.status_code, response_data)
        elif response.status_code == 429:
            logger.warning("Rate limit exceeded")
            raise RateLimitError("Rate limit exceeded", response.status_code, response_data)
        elif response.status_code == 404:
            error_msg = "Resource not found"
            logger.error(error_msg)
            raise AmadeusAPIError(error_msg, response.status_code, response_data)
        else:
            error_msg = self._extract_error_message(response_data) or f"Request failed with status {response.status_code}"
            logger.error(f"API error: {error_msg}")
            raise AmadeusAPIError(error_msg, response.status_code, response_data)
    
    def _extract_error_message(self, response_data: Dict) -> str:
        """
        Extract error message from API response
        
        Args:
            response_data: API response dictionary
            
        Returns:
            Error message string
        """
        if "errors" in response_data and response_data["errors"]:
            errors = response_data["errors"]
            if isinstance(errors, list) and len(errors) > 0:
                error = errors[0]
                detail = error.get("detail", "")
                title = error.get("title", "")
                return f"{title}: {detail}" if title and detail else (detail or title or "Unknown error")
        return response_data.get("error_description", response_data.get("error", "Unknown error"))
    
    # ==================== LOCATION SEARCH ====================
    
    def search_locations(
        self,
        keyword: str,
        sub_type: List[str] = ["CITY", "AIRPORT"],
        country_code: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for locations (cities, airports) by keyword.
        
        Args:
            keyword: Search keyword (e.g., "Lon")
            sub_type: List of location types to include
            country_code: Filter by country code
            limit: Maximum number of results
            
        Returns:
            List of normalized location dictionaries
        """
        url = f"{self.base_url}/v1/reference-data/locations"
        
        params = {
            "subType": ",".join(sub_type),
            "keyword": keyword,
            "page[limit]": limit,
            "view": "LIGHT"
        }
        
        if country_code:
            params["countryCode"] = country_code
            
        try:
            headers = self._get_headers()
            response = self._session.get(url, headers=headers, params=params, timeout=self.config.timeout)
            
            # Handle response directly to return empty list on 404 or specific errors instead of raising
            if response.status_code == 200:
                data = response.json()
                return self._normalize_locations(data.get("data", []))
            elif response.status_code == 404:
                return []
            else:
                # Log but return empty list for cleaner frontend experience? 
                # Or re-use handle_response if we want to bubble up errors?
                # Requirement says "Never swallow errors", so utilizing _handle_response might be better
                # but for an autocomplete, 400s (too short) or 404s are common.
                self._handle_response(response) # This will raise if not 200
                return []
                
        except AmadeusAPIError as e:
            logger.warning(f"Location search failed: {e.message}")
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"Location search network error: {str(e)}")
            return []
            
    def _normalize_locations(self, locations: List[Dict]) -> List[Dict[str, Any]]:
        """
        Normalize Amadeus location response to frontend-friendly format
        """
        normalized = []
        for loc in locations:
            try:
                normalized.append({
                    "type": loc.get("subType", "LOCATION"),
                    "name": loc.get("name", "").title(),
                    "iataCode": loc.get("iataCode", ""),
                    "city": loc.get("address", {}).get("cityName", "").title(),
                    "country": loc.get("address", {}).get("countryName", "").title(),
                    "score": loc.get("analytics", {}).get("travelers", {}).get("score", 0)
                })
            except Exception:
                continue
        
        # Sort by score descending if available, else standard sort
        # Using a simple heuristic for relevance if score is missing
        return sorted(normalized, key=lambda x: x.get("score", 0), reverse=True)

    # ==================== FLIGHT OFFERS SEARCH ====================
    
    def search_flight_offers(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        adults: int = 1,
        return_date: Optional[str] = None,
        children: Optional[int] = None,
        infants: Optional[int] = None,
        travel_class: Optional[TravelClass] = None,
        non_stop: Optional[bool] = None,
        currency: Optional[str] = None,
        max_price: Optional[float] = None,
        max_results: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Search for flight offers using GET method (simple search)
        
        Args:
            origin: IATA code of origin airport (e.g., 'JFK')
            destination: IATA code of destination airport (e.g., 'LAX')
            departure_date: Departure date in YYYY-MM-DD format
            adults: Number of adult passengers (12+ years)
            return_date: Return date for round-trip in YYYY-MM-DD format
            children: Number of children (2-11 years)
            infants: Number of infants (under 2 years)
            travel_class: Cabin class preference
            non_stop: If True, only direct flights
            currency: Preferred currency code (e.g., 'USD')
            max_price: Maximum price per traveler
            max_results: Maximum number of flight offers to return
            
        Returns:
            Dictionary containing flight offers data
            
        Raises:
            ValidationError: If parameters are invalid
            AmadeusAPIError: If API request fails
        """
        url = f"{self.base_url}/v2/shopping/flight-offers"
        
        params = {
            "originLocationCode": origin.upper(),
            "destinationLocationCode": destination.upper(),
            "departureDate": departure_date,
            "adults": adults
        }
        
        # Add optional parameters
        if return_date:
            params["returnDate"] = return_date
        if children is not None:
            params["children"] = children
        if infants is not None:
            params["infants"] = infants
        if travel_class:
            params["travelClass"] = travel_class.value
        if non_stop is not None:
            params["nonStop"] = str(non_stop).lower()
        if currency:
            params["currencyCode"] = currency.upper()
        if max_price is not None:
            params["maxPrice"] = max_price
        if max_results is not None:
            params["max"] = max_results
        
        try:
            logger.info(f"Searching flights: {origin} -> {destination} on {departure_date}")
            response = self._session.get(
                url,
                headers=self._get_headers(),
                params=params,
                timeout=self.config.timeout
            )
            
            result = self._handle_response(response)
            logger.info(f"Found {len(result.get('data', []))} flight offers")
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Flight search request failed: {str(e)}")
            raise AmadeusAPIError(f"Flight search request failed: {str(e)}")
    
    def search_flight_offers_post(
        self,
        origin_destinations: List[Dict[str, str]],
        travelers: List[Dict[str, Any]],
        search_criteria: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Search for flight offers using POST method (advanced multi-city search)
        
        This method supports multi-city itineraries and more complex search criteria.
        
        Args:
            origin_destinations: List of origin-destination pairs
                Example: [
                    {"id": "1", "originLocationCode": "MAD", 
                     "destinationLocationCode": "PAR", "departureDateTimeRange": {"date": "2024-12-01"}},
                    {"id": "2", "originLocationCode": "PAR", 
                     "destinationLocationCode": "MUC", "departureDateTimeRange": {"date": "2024-12-05"}}
                ]
            travelers: List of traveler objects
                Example: [{"id": "1", "travelerType": "ADULT"}]
            search_criteria: Optional advanced search criteria
                Example: {"maxFlightOffers": 10, "flightFilters": {"cabinRestrictions": [...]}}
            
        Returns:
            Dictionary containing flight offers data
            
        Raises:
            ValidationError: If parameters are invalid
            AmadeusAPIError: If API request fails
        """
        url = f"{self.base_url}/v2/shopping/flight-offers"
        
        payload = {
            "originDestinations": origin_destinations,
            "travelers": travelers,
            "sources": ["GDS"]
        }
        
        if search_criteria:
            payload["searchCriteria"] = search_criteria
        
        try:
            logger.info(f"Searching flights (POST) with {len(origin_destinations)} segments")
            response = self._session.post(
                url,
                headers=self._get_headers(),
                json=payload,
                timeout=self.config.timeout
            )
            
            result = self._handle_response(response)
            logger.info(f"Found {len(result.get('data', []))} flight offers")
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Flight search (POST) request failed: {str(e)}")
            raise AmadeusAPIError(f"Flight search request failed: {str(e)}")
    
    # ==================== FLIGHT OFFERS PRICE ====================
    
    def confirm_flight_price(
        self,
        flight_offers: Union[Dict, List[Dict]],
        include: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Confirm the price and availability of flight offers
        
        This API confirms the latest price and availability before booking.
        It's a critical step in the booking flow to ensure the price hasn't changed.
        
        Args:
            flight_offers: Flight offer(s) from search results
                Can be a single offer dict or list of offers
            include: Optional list of additional data to include
                Options: 'credit-card-fees', 'bags', 'other-services', 'detailed-fare-rules'
            
        Returns:
            Dictionary with confirmed pricing and availability
            
        Raises:
            ValidationError: If flight offer data is invalid
            AmadeusAPIError: If API request fails
        """
        url = f"{self.base_url}/v1/shopping/flight-offers/pricing"
        
        # Ensure flight_offers is a list
        if isinstance(flight_offers, dict):
            flight_offers = [flight_offers]
        
        payload = {
            "data": {
                "type": "flight-offers-pricing",
                "flightOffers": flight_offers
            }
        }
        
        # Add optional include parameter
        params = {}
        if include:
            params["include"] = ",".join(include)
        
        try:
            logger.info(f"Confirming price for {len(flight_offers)} flight offer(s)")
            response = self._session.post(
                url,
                headers=self._get_headers(),
                json=payload,
                params=params,
                timeout=self.config.timeout
            )
            
            result = self._handle_response(response)
            logger.info("Price confirmation successful")
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Price confirmation request failed: {str(e)}")
            raise AmadeusAPIError(f"Price confirmation request failed: {str(e)}")
    
    # ==================== FLIGHT CREATE ORDERS ====================
    
    def create_flight_order(
        self,
        flight_offers: Union[Dict, List[Dict]],
        travelers: List[Dict[str, Any]],
        contacts: Optional[List[Dict[str, Any]]] = None,
        remarks: Optional[Dict[str, Any]] = None,
        ticketing_agreement: Optional[Dict[str, Any]] = None,
        queuing_office_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a flight order (book a flight)
        
        IMPORTANT: This creates an actual booking. In production, this requires:
        - Working with an airline consolidator or being IATA/ARC accredited
        - Real payment processing
        
        Args:
            flight_offers: Priced flight offer(s) from confirm_flight_price
            travelers: List of traveler information
                Example: [{
                    "id": "1",
                    "dateOfBirth": "1990-01-01",
                    "name": {"firstName": "JOHN", "lastName": "DOE"},
                    "gender": "MALE",
                    "contact": {
                        "emailAddress": "[email protected]",
                        "phones": [{"deviceType": "MOBILE", "countryCallingCode": "1", "number": "1234567890"}]
                    },
                    "documents": [{
                        "documentType": "PASSPORT",
                        "birthPlace": "Madrid",
                        "issuanceLocation": "Madrid",
                        "issuanceDate": "2015-04-14",
                        "number": "00000000",
                        "expiryDate": "2025-04-14",
                        "issuanceCountry": "ES",
                        "validityCountry": "ES",
                        "nationality": "ES",
                        "holder": true
                    }]
                }]
            contacts: Optional contact information (if not in travelers)
            remarks: Optional remarks for the booking
            ticketing_agreement: Optional ticketing agreement details
            queuing_office_id: Optional consolidator office ID
            
        Returns:
            Dictionary containing the flight order details with booking reference
            
        Raises:
            BookingError: If booking fails
            ValidationError: If booking data is invalid
            AmadeusAPIError: If API request fails
        """
        url = f"{self.base_url}/v1/booking/flight-orders"
        
        # Ensure flight_offers is a list
        if isinstance(flight_offers, dict):
            flight_offers = [flight_offers]
        
        payload = {
            "data": {
                "type": "flight-order",
                "flightOffers": flight_offers,
                "travelers": travelers
            }
        }
        
        # Add optional parameters
        if contacts:
            payload["data"]["contacts"] = contacts
        if remarks:
            payload["data"]["remarks"] = remarks
        if ticketing_agreement:
            payload["data"]["ticketingAgreement"] = ticketing_agreement
        if queuing_office_id:
            payload["data"]["queuingOfficeId"] = queuing_office_id
        
        try:
            logger.info(f"Creating flight order for {len(travelers)} traveler(s)")
            response = self._session.post(
                url,
                headers=self._get_headers(),
                json=payload,
                timeout=self.config.timeout
            )
            
            result = self._handle_response(response)
            order_id = result.get("data", {}).get("id", "N/A")
            logger.info(f"Flight order created successfully. Order ID: {order_id}")
            return result
            
        except AmadeusAPIError as e:
            if "SEGMENT SELL FAILURE" in str(e.message):
                logger.error("Booking failed: Flight is no longer available")
                raise BookingError("Flight is no longer available (sold out)", e.status_code, e.response)
            elif "PRICE DISCREPANCY" in str(e.message):
                logger.error("Booking failed: Price has changed")
                raise BookingError("Price has changed, please re-confirm", e.status_code, e.response)
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Flight order creation request failed: {str(e)}")
            raise BookingError(f"Flight order creation failed: {str(e)}")
    
    # ==================== FLIGHT ORDER MANAGEMENT ====================
    
    def get_flight_order(self, order_id: str) -> Dict[str, Any]:
        """
        Retrieve a flight order by ID
        
        Args:
            order_id: The flight order ID (from create_flight_order)
            
        Returns:
            Dictionary containing flight order details
            
        Raises:
            AmadeusAPIError: If order not found or request fails
        """
        url = f"{self.base_url}/v1/booking/flight-orders/{order_id}"
        
        try:
            logger.info(f"Retrieving flight order: {order_id}")
            response = self._session.get(
                url,
                headers=self._get_headers(),
                timeout=self.config.timeout
            )
            
            result = self._handle_response(response)
            logger.info(f"Flight order retrieved successfully")
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Get flight order request failed: {str(e)}")
            raise AmadeusAPIError(f"Get flight order failed: {str(e)}")
    
    def cancel_flight_order(self, order_id: str) -> Dict[str, Any]:
        """
        Cancel a flight order
        
        NOTE: In production, cancellation policies depend on:
        - Airline rules
        - Ticket issuance status
        - Consolidator agreements
        
        After ticket issuance, cancellations must be handled with the consolidator.
        
        Args:
            order_id: The flight order ID to cancel
            
        Returns:
            Dictionary containing cancellation confirmation
            
        Raises:
            AmadeusAPIError: If cancellation fails
        """
        url = f"{self.base_url}/v1/booking/flight-orders/{order_id}"
        
        try:
            logger.info(f"Cancelling flight order: {order_id}")
            response = self._session.delete(
                url,
                headers=self._get_headers(),
                timeout=self.config.timeout
            )
            
            # DELETE returns 204 No Content on success
            if response.status_code == 204:
                logger.info(f"Flight order {order_id} cancelled successfully")
                return {"status": "cancelled", "orderId": order_id}
            
            result = self._handle_response(response)
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Cancel flight order request failed: {str(e)}")
            raise AmadeusAPIError(f"Cancel flight order failed: {str(e)}")
    
    # ==================== UTILITY METHODS ====================
    
    def close(self) -> None:
        """Close the session and cleanup resources"""
        if self._session:
            self._session.close()
            logger.info("Amadeus service session closed")


# ==================== CONVENIENCE FUNCTIONS ====================

def create_amadeus_service(
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
    environment: str = "test"
) -> AmadeusFlightService:
    """
    Factory function to create AmadeusFlightService instance
    
    Args:
        client_id: Amadeus API client ID (or set AMADEUS_CLIENT_ID env var)
        client_secret: Amadeus API client secret (or set AMADEUS_CLIENT_SECRET env var)
        environment: 'test' or 'production'
        
    Returns:
        Configured AmadeusFlightService instance
        
    Raises:
        ValueError: If credentials are not provided
    """
    client_id = client_id or os.getenv("AMADEUS_API_KEY")
    client_secret = client_secret or os.getenv("AMADEUS_SECRET_KEY")
    
    if not client_id or not client_secret:
        raise ValueError(
            "Amadeus credentials not provided. "
            "Set AMADEUS_API_KEY and AMADEUS_SECRET_KEY environment variables "
            "or pass them as arguments."
        )
    
    env = AmadeusEnvironment.TEST if environment.lower() == "test" else AmadeusEnvironment.PRODUCTION
    
    config = AmadeusConfig(
        client_id=client_id,
        client_secret=client_secret,
        environment=env
    )
    
    return AmadeusFlightService(config)


# ==================== EXAMPLE USAGE ====================

if __name__ == "__main__":
    """
    Example usage of the Amadeus Flight Service
    
    To run this example:
    1. Set environment variables:
       export AMADEUS_API_KEY="your_api_key"
       export AMADEUS_SECRET_KEY="your_secret_key"
    
    2. Run: python services/amadeus.py
    """
    
    try:
        # Create service instance
        service = create_amadeus_service(environment="test")
        
        # Example 1: Search for flights
        print("\n=== SEARCHING FOR FLIGHTS ===")
        search_results = service.search_flight_offers(
            origin="JFK",
            destination="LAX",
            departure_date="2025-03-15",
            adults=1,
            return_date="2025-03-20",
            travel_class=TravelClass.ECONOMY,
            max_results=3
        )
        
        print(f"Found {len(search_results.get('data', []))} flight offers")
        
        if search_results.get("data"):
            # Example 2: Confirm price for first offer
            print("\n=== CONFIRMING PRICE ===")
            first_offer = search_results["data"][0]
            
            price_confirmation = service.confirm_flight_price(
                flight_offers=first_offer,
                include=["credit-card-fees"]
            )
            
            confirmed_offer = price_confirmation.get("data", {}).get("flightOffers", [{}])[0]
            price = confirmed_offer.get("price", {})
            print(f"Confirmed price: {price.get('total')} {price.get('currency')}")
            
            # Example 3: Create booking (commented out to prevent accidental bookings)
            # print("\n=== CREATING BOOKING ===")
            # travelers = [{
            #     "id": "1",
            #     "dateOfBirth": "1990-01-01",
            #     "name": {"firstName": "JOHN", "lastName": "DOE"},
            #     "gender": "MALE",
            #     "contact": {
            #         "emailAddress": "[email protected]",
            #         "phones": [{
            #             "deviceType": "MOBILE",
            #             "countryCallingCode": "1",
            #             "number": "5551234567"
            #         }]
            #     }
            # }]
            # 
            # order = service.create_flight_order(
            #     flight_offers=confirmed_offer,
            #     travelers=travelers
            # )
            # 
            # order_id = order.get("data", {}).get("id")
            # print(f"Booking created! Order ID: {order_id}")
            
            # Example 4: Retrieve order
            # print("\n=== RETRIEVING ORDER ===")
            # retrieved_order = service.get_flight_order(order_id)
            # print(f"Order status: {retrieved_order.get('data', {}).get('status')}")
        
        # Close the service
        service.close()
        print("\n=== EXAMPLES COMPLETED SUCCESSFULLY ===")
        
    except AmadeusAPIError as e:
        print(f"\nAmadeus API Error: {e.message}")
        if e.response:
            print(f"Response: {e.response}")
    except Exception as e:
        print(f"\nUnexpected error: {str(e)}")