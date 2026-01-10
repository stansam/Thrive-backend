# sample_data.py
# Sample package data for loading into the database

from datetime import date, timedelta

# Calculate dynamic dates
today = date.today()
available_from = today
available_until = today + timedelta(days=365)

SAMPLE_PACKAGES = [
    # 1. Dubai Luxury Escape (Featured - Created First)
    {
        'name': 'Dubai Luxury Escape',
        'slug': 'dubai-luxury-escape',
        'short_description': 'Experience the best of Dubai with luxury accommodations, iconic attractions, and unforgettable desert adventures.',
        'full_description': 'Immerse yourself in the opulence and wonder of Dubai with our carefully curated 5-day luxury escape. From the towering Burj Khalifa to the serene desert dunes, experience the perfect blend of modern luxury and Arabian tradition. Stay in a premium 4-star hotel in Downtown Dubai, enjoy a thrilling desert safari with BBQ dinner, cruise the Marina in style, and explore the architectural marvel of Abu Dhabi\'s Grand Mosque. This package offers the ultimate Dubai experience for discerning travelers.',
        'destination_city': 'Dubai',
        'destination_country': 'United Arab Emirates',
        'duration_days': 5,
        'duration_nights': 4,
        'starting_price': 1899.00,
        'price_per_person': 1899.00,
        'highlights': [
            '4-star hotel in Downtown Dubai',
            'Desert Safari + BBQ dinner',
            'Dubai Marina Yacht Cruise',
            'Burj Khalifa At-The-Top experience',
            'Dubai Mall + Fountain show',
            'Abu Dhabi Grand Mosque tour'
        ],
        'inclusions': [
            'Hotel accommodation',
            'Breakfast daily',
            'Airport transfers',
            'All tours & activities',
            'Professional guide',
            'Entrance fees'
        ],
        'exclusions': [
            'International flights (can be added)',
            'Travel insurance',
            'Personal expenses',
            'Lunch and dinner (except desert safari)',
            'Visa fees'
        ],
        'itinerary': [
            {
                'day': 1,
                'title': 'Arrival in Dubai',
                'description': 'Arrive at Dubai International Airport. Meet and greet by our representative. Transfer to your hotel in Downtown Dubai. Check-in and rest. Evening at leisure to explore Dubai Mall and watch the spectacular Fountain Show.',
                'activities': ['Airport pickup', 'Hotel check-in', 'Dubai Mall visit', 'Fountain Show']
            },
            {
                'day': 2,
                'title': 'Dubai City Tour & Burj Khalifa',
                'description': 'Morning city tour covering key landmarks. Afternoon visit to Burj Khalifa At-The-Top observation deck on the 124th floor. Enjoy panoramic views of the city skyline.',
                'activities': ['Dubai Museum', 'Gold Souk', 'Spice Souk', 'Burj Al Arab photo stop', 'Burj Khalifa visit']
            },
            {
                'day': 3,
                'title': 'Desert Safari Adventure',
                'description': 'Morning at leisure. Afternoon pickup for desert safari adventure. Experience dune bashing, camel riding, sandboarding, and traditional entertainment. Enjoy a delicious BBQ dinner under the stars.',
                'activities': ['Dune bashing', 'Camel riding', 'Sandboarding', 'Henna painting', 'BBQ dinner', 'Belly dance show']
            },
            {
                'day': 4,
                'title': 'Dubai Marina & Abu Dhabi',
                'description': 'Morning yacht cruise in Dubai Marina. Afternoon excursion to Abu Dhabi to visit the magnificent Sheikh Zayed Grand Mosque. Return to Dubai in the evening.',
                'activities': ['Dubai Marina Yacht Cruise', 'Drive to Abu Dhabi', 'Grand Mosque tour', 'Corniche photo stop']
            },
            {
                'day': 5,
                'title': 'Departure',
                'description': 'Enjoy breakfast at the hotel. Check-out and transfer to Dubai International Airport for your departure flight. Take home unforgettable memories of Dubai.',
                'activities': ['Hotel breakfast', 'Check-out', 'Airport transfer']
            }
        ],
        'hotel_name': 'Downtown Dubai Premium Hotel',
        'hotel_rating': 4,
        'hotel_address': 'Sheikh Mohammed bin Rashid Boulevard, Downtown Dubai',
        'hotel_phone': '+971-4-123-4567',
        'room_type': 'Deluxe Room with Burj Khalifa View',
        'is_active': True,
        'available_from': available_from.isoformat(),
        'available_until': available_until.isoformat(),
        'max_capacity': 50,
        'min_booking': 1,
        'is_featured': True,
        'marketing_tagline': 'Yacht Cruise • Desert Safari • Burj Khalifa',
        'featured_image': 'https://images.unsplash.com/photo-1512453979798-5ea266f8880c',
        'gallery_images': [
            'https://images.unsplash.com/photo-1512453979798-5ea266f8880c',
            'https://images.unsplash.com/photo-1518684079-3c830dcef090',
            'https://images.unsplash.com/photo-1580674285054-bed31e145f59'
        ],
        'meta_title': 'Dubai Luxury Escape - 5 Days Premium Tour Package',
        'meta_description': 'Book your Dubai luxury vacation with our 5-day package featuring Burj Khalifa, Desert Safari, Marina Cruise, and more. Starting at $1,899 per person.',
        'view_count': 245,
        'booking_count': 18
    },
    
    # 2. Maldives Paradise Retreat
    {
        'name': 'Maldives Paradise Retreat',
        'slug': 'maldives-paradise-retreat',
        'short_description': 'Escape to a tropical paradise with overwater villas, pristine beaches, and world-class snorkeling.',
        'full_description': 'Discover the ultimate island getaway in the Maldives. Stay in a luxurious overwater villa, dive into crystal-clear waters teeming with marine life, and unwind on powder-white beaches. This all-inclusive package offers the perfect romantic escape or family vacation in one of the world\'s most beautiful destinations.',
        'destination_city': 'Male',
        'destination_country': 'Maldives',
        'duration_days': 6,
        'duration_nights': 5,
        'starting_price': 3499.00,
        'price_per_person': 3499.00,
        'highlights': [
            'Overwater villa accommodation',
            'All-inclusive meals and drinks',
            'Snorkeling and diving excursions',
            'Sunset cruise',
            'Spa treatment session',
            'Water sports activities'
        ],
        'inclusions': [
            'Overwater villa',
            'All meals (breakfast, lunch, dinner)',
            'Soft drinks and selected alcoholic beverages',
            'Speedboat transfers',
            'Snorkeling equipment',
            'One spa treatment per person'
        ],
        'exclusions': [
            'International flights',
            'Travel insurance',
            'Premium alcoholic beverages',
            'Additional spa treatments',
            'Diving certification courses'
        ],
        'itinerary': [
            {
                'day': 1,
                'title': 'Arrival & Island Welcome',
                'description': 'Arrive at Male International Airport. Speedboat transfer to resort island. Welcome drink and check-in to your overwater villa. Afternoon at leisure to explore the island.',
                'activities': ['Airport pickup', 'Speedboat transfer', 'Villa check-in', 'Island orientation']
            },
            {
                'day': 2,
                'title': 'Snorkeling Adventure',
                'description': 'Morning snorkeling excursion to vibrant coral reefs. Afternoon relaxation on the beach or by the villa deck. Evening sunset viewing.',
                'activities': ['Snorkeling trip', 'Beach time', 'Sunset photography']
            },
            {
                'day': 3,
                'title': 'Water Sports & Spa',
                'description': 'Morning water sports activities including kayaking and paddleboarding. Afternoon spa treatment. Evening sunset cruise.',
                'activities': ['Kayaking', 'Paddleboarding', 'Spa treatment', 'Sunset cruise']
            },
            {
                'day': 4,
                'title': 'Island Hopping',
                'description': 'Full-day island hopping excursion. Visit local islands, experience Maldivian culture, and enjoy a beachside lunch.',
                'activities': ['Island hopping', 'Local village visit', 'Beach BBQ lunch', 'Souvenir shopping']
            },
            {
                'day': 5,
                'title': 'Leisure Day',
                'description': 'Day at leisure to enjoy resort facilities. Optional diving excursion or additional spa treatments (at extra cost).',
                'activities': ['Free time', 'Optional activities', 'Farewell dinner']
            },
            {
                'day': 6,
                'title': 'Departure',
                'description': 'Breakfast at villa. Check-out and speedboat transfer to Male Airport.',
                'activities': ['Breakfast', 'Check-out', 'Airport transfer']
            }
        ],
        'hotel_name': 'Paradise Island Resort & Spa',
        'hotel_rating': 5,
        'hotel_address': 'Lankanfinolhu Island, North Male Atoll',
        'hotel_phone': '+960-664-3737',
        'room_type': 'Overwater Villa with Private Deck',
        'is_active': True,
        'available_from': available_from.isoformat(),
        'available_until': available_until.isoformat(),
        'max_capacity': 30,
        'min_booking': 2,
        'is_featured': True,
        'marketing_tagline': 'Overwater Villas • Pristine Beaches • Crystal Waters',
        'featured_image': 'https://images.unsplash.com/photo-1512453979798-5ea266f8880c',
        'gallery_images': [
            'https://images.unsplash.com/photo-1512453979798-5ea266f8880c',
            'https://images.unsplash.com/photo-1518684079-3c830dcef090',
            'https://images.unsplash.com/photo-1580674285054-bed31e145f59'
        ],
        'meta_title': 'Maldives Paradise Retreat - 6 Days All-Inclusive Resort',
        'meta_description': 'Book your dream Maldives vacation with overwater villas, all-inclusive dining, and water activities. From $3,499 per person.',
        'view_count': 189,
        'booking_count': 12
    },
    
    # 3. European Grand Tour
    {
        'name': 'European Grand Tour',
        'slug': 'european-grand-tour',
        'short_description': 'Explore the best of Europe: Paris, Rome, Barcelona, and Amsterdam in one incredible journey.',
        'full_description': 'Experience the magic of Europe with our comprehensive 12-day tour covering four iconic cities. From the romantic streets of Paris to the ancient ruins of Rome, the artistic flair of Barcelona, and the charming canals of Amsterdam, this tour offers a perfect blend of culture, history, and cuisine.',
        'destination_city': 'Paris',
        'destination_country': 'France',
        'duration_days': 12,
        'duration_nights': 11,
        'starting_price': 2799.00,
        'price_per_person': 2799.00,
        'highlights': [
            'Visit 4 European capitals',
            'Eiffel Tower and Louvre Museum',
            'Vatican and Colosseum tours',
            'Sagrada Familia visit',
            'Amsterdam canal cruise',
            'High-speed train journeys'
        ],
        'inclusions': [
            '3-star hotels in city centers',
            'Daily breakfast',
            'Inter-city train tickets',
            'Guided city tours',
            'Entrance fees to major attractions',
            'Professional tour manager'
        ],
        'exclusions': [
            'International flights',
            'Lunch and dinner',
            'Travel insurance',
            'Optional excursions',
            'Personal expenses'
        ],
        'itinerary': [
            {
                'day': 1,
                'title': 'Arrival in Paris',
                'description': 'Arrive in Paris. Check-in to hotel. Evening Seine River cruise.',
                'activities': ['Hotel check-in', 'Seine River cruise', 'Welcome dinner']
            },
            {
                'day': 2,
                'title': 'Paris Highlights',
                'description': 'Eiffel Tower visit. Louvre Museum tour. Evening at Champs-Élysées.',
                'activities': ['Eiffel Tower', 'Louvre Museum', 'Arc de Triomphe']
            },
            {
                'day': 3,
                'title': 'Paris to Rome',
                'description': 'Morning at leisure. Afternoon train to Rome. Evening arrival and check-in.',
                'activities': ['Free morning', 'Train journey', 'Rome arrival']
            },
            {
                'day': 4,
                'title': 'Ancient Rome',
                'description': 'Colosseum and Roman Forum tour. Trevi Fountain and Spanish Steps.',
                'activities': ['Colosseum', 'Roman Forum', 'Trevi Fountain']
            },
            {
                'day': 5,
                'title': 'Vatican City',
                'description': 'Vatican Museums and Sistine Chapel. St. Peter\'s Basilica tour.',
                'activities': ['Vatican Museums', 'Sistine Chapel', 'St. Peter\'s Basilica']
            },
            {
                'day': 6,
                'title': 'Rome to Barcelona',
                'description': 'Train journey to Barcelona. Evening arrival and tapas dinner.',
                'activities': ['Train travel', 'Barcelona arrival', 'Tapas tour']
            },
            {
                'day': 7,
                'title': 'Gaudí\'s Barcelona',
                'description': 'Sagrada Familia visit. Park Güell exploration. Gothic Quarter walk.',
                'activities': ['Sagrada Familia', 'Park Güell', 'Gothic Quarter']
            },
            {
                'day': 8,
                'title': 'Barcelona Beach & Culture',
                'description': 'La Rambla stroll. Barceloneta Beach. Evening flamenco show.',
                'activities': ['La Rambla', 'Beach time', 'Flamenco performance']
            },
            {
                'day': 9,
                'title': 'Barcelona to Amsterdam',
                'description': 'Flight to Amsterdam. Canal district exploration.',
                'activities': ['Flight', 'Canal walk', 'Hotel check-in']
            },
            {
                'day': 10,
                'title': 'Amsterdam Museums',
                'description': 'Anne Frank House. Van Gogh Museum. Rijksmuseum visit.',
                'activities': ['Anne Frank House', 'Van Gogh Museum', 'Rijksmuseum']
            },
            {
                'day': 11,
                'title': 'Amsterdam Canals & Culture',
                'description': 'Canal cruise. Flower market. Evening in Jordaan district.',
                'activities': ['Canal cruise', 'Flower market', 'Jordaan exploration']
            },
            {
                'day': 12,
                'title': 'Departure',
                'description': 'Final breakfast. Check-out and airport transfer.',
                'activities': ['Breakfast', 'Check-out', 'Airport transfer']
            }
        ],
        'hotel_name': 'Various 3-Star City Center Hotels',
        'hotel_rating': 3,
        'hotel_address': 'Central locations in each city',
        'hotel_phone': '+33-1-234-5678',
        'room_type': 'Standard Double/Twin Room',
        'is_active': True,
        'available_from': available_from.isoformat(),
        'available_until': available_until.isoformat(),
        'max_capacity': 40,
        'min_booking': 1,
        'is_featured': False,
        'marketing_tagline': 'Paris • Rome • Barcelona • Amsterdam',
        'featured_image': 'https://images.unsplash.com/photo-1512453979798-5ea266f8880c',
        'gallery_images': [
            'https://images.unsplash.com/photo-1512453979798-5ea266f8880c',
            'https://images.unsplash.com/photo-1518684079-3c830dcef090',
            'https://images.unsplash.com/photo-1580674285054-bed31e145f59'
        ],
        'meta_title': 'European Grand Tour - 12 Days Multi-City Package',
        'meta_description': 'Explore Paris, Rome, Barcelona, and Amsterdam in 12 days. Comprehensive tour with hotels, trains, and guided tours. From $2,799.',
        'view_count': 312,
        'booking_count': 23
    },
    
    # 4. Bali Wellness Retreat
    {
        'name': 'Bali Wellness Retreat',
        'slug': 'bali-wellness-retreat',
        'short_description': 'Rejuvenate your mind, body, and soul in Bali\'s serene landscapes with yoga, spa, and meditation.',
        'full_description': 'Find your inner peace in the spiritual heart of Bali. This wellness-focused retreat combines daily yoga sessions, traditional Balinese spa treatments, meditation classes, and healthy organic cuisine. Stay in a tranquil resort surrounded by rice terraces and tropical gardens.',
        'destination_city': 'Ubud',
        'destination_country': 'Indonesia',
        'duration_days': 7,
        'duration_nights': 6,
        'starting_price': 1599.00,
        'price_per_person': 1599.00,
        'highlights': [
            'Daily yoga and meditation sessions',
            '3 traditional Balinese spa treatments',
            'Organic vegetarian meals',
            'Rice terrace trekking',
            'Temple visits',
            'Cooking class'
        ],
        'inclusions': [
            'Boutique resort accommodation',
            'All meals (vegetarian/vegan)',
            'Daily yoga classes',
            'Meditation sessions',
            '3 spa treatments',
            'Airport transfers',
            'Cultural excursions'
        ],
        'exclusions': [
            'International flights',
            'Travel insurance',
            'Additional spa treatments',
            'Personal expenses',
            'Alcoholic beverages'
        ],
        'itinerary': [
            {
                'day': 1,
                'title': 'Arrival & Welcome',
                'description': 'Airport pickup. Transfer to Ubud resort. Welcome ceremony and orientation. Evening meditation session.',
                'activities': ['Airport transfer', 'Check-in', 'Welcome ceremony', 'Evening meditation']
            },
            {
                'day': 2,
                'title': 'Yoga & Temple Visit',
                'description': 'Morning yoga session. Healthy breakfast. Visit Tirta Empul holy water temple. Afternoon spa treatment.',
                'activities': ['Morning yoga', 'Temple visit', 'Holy water purification', 'Spa treatment']
            },
            {
                'day': 3,
                'title': 'Rice Terrace Trek',
                'description': 'Sunrise yoga. Guided trek through Tegalalang rice terraces. Organic lunch. Afternoon meditation and free time.',
                'activities': ['Sunrise yoga', 'Rice terrace trek', 'Nature photography', 'Meditation']
            },
            {
                'day': 4,
                'title': 'Cultural Immersion',
                'description': 'Morning yoga. Traditional Balinese cooking class. Visit local market. Evening cultural performance.',
                'activities': ['Yoga session', 'Cooking class', 'Market visit', 'Dance performance']
            },
            {
                'day': 5,
                'title': 'Wellness & Healing',
                'description': 'Morning yoga and pranayama. Full-body Balinese massage. Healing meditation. Wellness consultation.',
                'activities': ['Yoga', 'Pranayama', 'Massage', 'Wellness consultation']
            },
            {
                'day': 6,
                'title': 'Waterfall & Spa',
                'description': 'Visit Tegenungan waterfall. Natural pool swimming. Afternoon spa ritual. Farewell dinner.',
                'activities': ['Waterfall visit', 'Swimming', 'Spa ritual', 'Farewell ceremony']
            },
            {
                'day': 7,
                'title': 'Departure',
                'description': 'Final yoga session. Healthy breakfast. Check-out and airport transfer.',
                'activities': ['Morning yoga', 'Breakfast', 'Check-out', 'Airport transfer']
            }
        ],
        'hotel_name': 'Ubud Wellness Resort',
        'hotel_rating': 4,
        'hotel_address': 'Jalan Raya Tegallalang, Ubud',
        'hotel_phone': '+62-361-123-4567',
        'room_type': 'Garden View Villa',
        'is_active': True,
        'available_from': available_from.isoformat(),
        'available_until': available_until.isoformat(),
        'max_capacity': 20,
        'min_booking': 1,
        'is_featured': True,
        'marketing_tagline': 'Yoga • Meditation • Spa • Organic Living',
        'featured_image': 'https://images.unsplash.com/photo-1512453979798-5ea266f8880c',
        'gallery_images': [
            'https://images.unsplash.com/photo-1512453979798-5ea266f8880c',
            'https://images.unsplash.com/photo-1518684079-3c830dcef090',
            'https://images.unsplash.com/photo-1580674285054-bed31e145f59'
        ],
        'meta_title': 'Bali Wellness Retreat - 7 Days Yoga & Spa Package',
        'meta_description': 'Rejuvenate in Ubud with daily yoga, meditation, spa treatments, and organic cuisine. Wellness retreat from $1,599.',
        'view_count': 156,
        'booking_count': 14
    },
    
    # 5. Safari Adventure Kenya
    {
        'name': 'Safari Adventure Kenya',
        'slug': 'safari-adventure-kenya',
        'short_description': 'Witness the great migration and experience Africa\'s wildlife in Kenya\'s premier national parks.',
        'full_description': 'Embark on the adventure of a lifetime with our comprehensive Kenya safari package. Explore the Masai Mara, Amboseli, and Lake Nakuru national parks. Witness the Big Five, experience the great migration (seasonal), and immerse yourself in Maasai culture. Stay in luxury tented camps under the African stars.',
        'destination_city': 'Nairobi',
        'destination_country': 'Kenya',
        'duration_days': 8,
        'duration_nights': 7,
        'starting_price': 2899.00,
        'price_per_person': 2899.00,
        'highlights': [
            'Masai Mara game drives',
            'Big Five wildlife spotting',
            'Great Migration viewing (seasonal)',
            'Visit to Maasai village',
            'Amboseli elephant herds',
            'Lake Nakuru flamingos'
        ],
        'inclusions': [
            'Luxury tented camp accommodation',
            'All meals',
            'Daily game drives',
            '4x4 safari vehicle',
            'Professional safari guide',
            'Park entrance fees',
            'Airport transfers'
        ],
        'exclusions': [
            'International flights',
            'Travel insurance',
            'Visa fees',
            'Alcoholic beverages',
            'Hot air balloon safari (optional)',
            'Gratuities'
        ],
        'itinerary': [
            {
                'day': 1,
                'title': 'Arrival in Nairobi',
                'description': 'Arrive at Jomo Kenyatta International Airport. Transfer to hotel in Nairobi. Briefing and rest.',
                'activities': ['Airport pickup', 'Hotel check-in', 'Safari briefing', 'Welcome dinner']
            },
            {
                'day': 2,
                'title': 'Nairobi to Masai Mara',
                'description': 'Drive to Masai Mara National Reserve. Afternoon game drive. Sunset at the savannah.',
                'activities': ['Drive to Masai Mara', 'First game drive', 'Camp check-in', 'Sunset viewing']
            },
            {
                'day': 3,
                'title': 'Full Day Masai Mara',
                'description': 'Full-day game drives in Masai Mara. Search for lions, elephants, leopards, buffalo, and rhinos. Picnic lunch in the wild.',
                'activities': ['Morning game drive', 'Bush breakfast', 'Afternoon game drive', 'Wildlife photography']
            },
            {
                'day': 4,
                'title': 'Masai Mara & Cultural Visit',
                'description': 'Morning game drive. Visit traditional Maasai village. Learn about Maasai culture and traditions.',
                'activities': ['Game drive', 'Maasai village visit', 'Cultural performance', 'Traditional lunch']
            },
            {
                'day': 5,
                'title': 'Lake Nakuru',
                'description': 'Drive to Lake Nakuru National Park. Famous for flamingos and rhino sanctuary. Afternoon game drive.',
                'activities': ['Drive to Nakuru', 'Flamingo viewing', 'Rhino tracking', 'Bird watching']
            },
            {
                'day': 6,
                'title': 'Lake Nakuru to Amboseli',
                'description': 'Journey to Amboseli National Park. Views of Mount Kilimanjaro. Evening game drive.',
                'activities': ['Scenic drive', 'Kilimanjaro views', 'Camp arrival', 'Evening game drive']
            },
            {
                'day': 7,
                'title': 'Amboseli Safari',
                'description': 'Full day exploring Amboseli. Famous for large elephant herds and Kilimanjaro backdrop. Optional visit to observation hill.',
                'activities': ['Sunrise game drive', 'Elephant observation', 'Swamp exploration', 'Sunset drive']
            },
            {
                'day': 8,
                'title': 'Return to Nairobi',
                'description': 'Morning game drive. Drive back to Nairobi. Optional souvenir shopping. Airport transfer.',
                'activities': ['Final game drive', 'Drive to Nairobi', 'Lunch', 'Airport transfer']
            }
        ],
        'hotel_name': 'Luxury Safari Camps (Various)',
        'hotel_rating': 4,
        'hotel_address': 'Various locations in national parks',
        'hotel_phone': '+254-20-123-4567',
        'room_type': 'Luxury Tented Suite',
        'is_active': True,
        'available_from': available_from.isoformat(),
        'available_until': available_until.isoformat(),
        'max_capacity': 24,
        'min_booking': 2,
        'is_featured': False,
        'marketing_tagline': 'Big Five • Great Migration • Maasai Culture',
        'featured_image': 'https://images.unsplash.com/photo-1512453979798-5ea266f8880c',
        'gallery_images': [
            'https://images.unsplash.com/photo-1512453979798-5ea266f8880c',
            'https://images.unsplash.com/photo-1518684079-3c830dcef090',
            'https://images.unsplash.com/photo-1580674285054-bed31e145f59'
        ],
        'meta_title': 'Kenya Safari Adventure - 8 Days Wildlife Tour',
        'meta_description': 'Experience Kenya\'s best wildlife parks including Masai Mara, Amboseli, and Lake Nakuru. Luxury safari from $2,899.',
        'view_count': 198,
        'booking_count': 16
    }
]