import React, { useState } from "react";
import { View, Text, TouchableOpacity } from "react-native";
import styles from "./dropdown.style";

// Define the type for the column headers
interface ColumnHeader {
  link: string;
  value: string;
  isActive: boolean;
}

// Props for the Dropdown component
interface DropdownProps {
  headers: ColumnHeader[];
  navigation: any; // Navigation object for screen navigation
}

const Dropdown: React.FC<DropdownProps> = ({ headers, navigation }) => {
  const [activeLink, setActiveLink] = useState<string | null>(null);

  const onPressHandler = (link: string) => {
    setActiveLink(link); // Update active link
    navigation.navigate(link); // Navigate to the link
  };

  return (
    <View style={styles.main}>
      <View style={styles.TopBox}>
        <View style={styles.headerBox}>
          {headers.map((header, index) => (
            <TouchableOpacity
              key={index}
              style={[
                styles.headerContainer,
                activeLink === header.link && styles.activeButton, // Apply activeButton style if link is active
              ]}
              onPress={() => onPressHandler(header.link)}
            >
              <Text style={styles.headerText}>{header.value}</Text>
            </TouchableOpacity>
          ))}
        </View>
      </View>
    </View>
  );
};

export default Dropdown;
