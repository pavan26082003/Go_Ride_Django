
# authicate, permission, token, status, response, generics, apiviews
from django.contrib.auth import authenticate
from rest_framework.permissions import IsAuthenticated
from rest_framework.authtoken.models import Token
from rest_framework import status, generics
from rest_framework.views import APIView
from .serializers import UserRegisterSerializer, BusSerializer, BookingSerializer
from rest_framework.response import Response
from .models import Bus, Seat, Booking

import razorpay
from django.conf import settings

class RegisterView(APIView):
    def post(self, request):
        serializer = UserRegisterSerializer(data= request.data)
        if serializer.is_valid():
            user = serializer.save()
            token, created = Token.objects.get_or_create(user=user)
            return Response({'token':token.key}, status= status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class LoginView(APIView):
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(username= username, password=password)

        if user:
            token, created = Token.objects.get_or_create(user=user)
            return Response({
                'token':token.key,
                'user_id': user.id
            }, status=status.HTTP_200_OK)
        else:
            return Response({'error':'Invalid Credentials'}, status=status.HTTP_401_UNAUTHORIZED)


class BusListCreateView(generics.ListCreateAPIView):
    queryset = Bus.objects.all()
    serializer_class = BusSerializer

class BusDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Bus.objects.all()
    serializer_class = BusSerializer

class BookingView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        seat_id = request.data.get('seat')
        try:
            seat = Seat.objects.get(id = seat_id)
            if seat.is_booked:
                return Response({'error': 'Seat already booked'}, status=status.HTTP_400_BAD_REQUEST)

            seat.is_booked = True
            seat.save()

            bookings = Booking.objects.create(
                user = request.user,
                bus = seat.bus,
                seat = seat
            )
            serializer = BookingSerializer(bookings)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Seat.DoesNotExist:
            return Response({'error':'Invalid Seat ID'}, status=status.HTTP_400_BAD_REQUEST)
        
class UserBookingView(APIView):
    permission_classes= [IsAuthenticated]

    def get(self, request, user_id):
        if request.user.id != user_id:
            return Response({'error':'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)
        
        bookings = Booking.objects.filter(user_id= user_id)
        serializer = BookingSerializer(bookings, many=True)
        return Response(serializer.data)
    

    # -------payment section

    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

class CreatePaymentOrderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        amount = int(request.data.get("amount", 0)) * 100  # amount in paise
        currency = "INR"
        receipt = f"receipt_{request.user.id}_{request.data.get('booking_id')}"

        order = client.order.create(dict(amount=amount, currency=currency, receipt=receipt))
        return Response(order)
    


class MarkBookingPaidView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        booking_id = request.data.get("booking_id")
        try:
            booking = Booking.objects.get(id=booking_id, user=request.user)
            booking.is_paid = True
            booking.save()
            return Response({"detail": "Payment successful and booking marked paid."})
        except Booking.DoesNotExist:
            return Response({"error": "Booking not found"}, status=404)
