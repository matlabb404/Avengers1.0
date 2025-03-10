import React from 'react';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import Booking from '@/pages/booking/Booking';
import Past from '@/pages/booking/book/past';
import Upcoming from '@/pages/booking/book/upcoming';

const BookingStack = createNativeStackNavigator();

const BookingNavigator = () => (
  <BookingStack.Navigator
    screenOptions={{ headerShown: false }}
    initialRouteName="Booking"
  >
    <BookingStack.Screen name="Booking" component={Booking} />
    <BookingStack.Screen name="Upcoming" component={Upcoming} />
    <BookingStack.Screen name="Past" component={Past} />
  </BookingStack.Navigator>
);

export default BookingNavigator;
