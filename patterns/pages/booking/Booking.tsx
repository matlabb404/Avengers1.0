import React, { useState } from 'react';
import { View, Text, TouchableOpacity } from 'react-native';
import styles from './booking.styles';

interface ColumnHeader {
  link: string;
  value: string;
  isActive: boolean;
}

interface bookingcomponents {
  navigation: any;
}

const Booking: React.FC<bookingcomponents> = ({ navigation }) => {
  const [headers, setHeaders] = useState<ColumnHeader[]>([
    { link: "Upcoming", value: "Upcoming", isActive: true },
    { link: "Past", value: "Past", isActive: false },
  ]);

  const [activeLink, setActiveLink] = useState<string | null>(null);

  const onPressHandler = (header: ColumnHeader) => {
    console.log(`Header pressed: ${header.value} (link: ${header.link})`);

    // Reset all headers to have isActive = false
    const updatedHeaders = headers.map((h) => ({
      ...h,
      isActive: h.link === header.link,
    }));

    setHeaders(updatedHeaders);

    // Update the active link and navigate
    setActiveLink(header.link);
    navigation.navigate(header.link);
  };

  return (
    <View style={{ height: '100%', marginTop: 10 }}>
      <View style={{ width: "100%" }}>
        <Text style={[styles.headerText]}>
          Bookings
        </Text>
      </View>
      <View style={styles.headerBox}>
        {headers.map((header, index) => (
          <TouchableOpacity
            key={index}
            style={[
              styles.headerContainer,
              header.isActive && styles.activeButton, // Apply activeButton style if link is active
            ]}
            onPress={() => onPressHandler(header)}
          >
            <Text style={[styles.headerText, { textAlign: 'center' }]}>{header.value}</Text>
          </TouchableOpacity>
        ))}
      </View>
    </View>
  );
};

export default Booking;
