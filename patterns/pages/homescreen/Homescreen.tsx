import React, { useState } from "react";
import { View, Text } from "react-native";
import Dropdown from "@/components/Dropdown/Dropdown"; // Import the Dropdown component
import Following from "../follow/Follow"; // Ensure this path is correct
import Discover from "../discover/Discover"; // Ensure this path is correct

// Define the column headers
const columnHeaders = [
  { link: "Discover", value: "Discover", isActive: false },
  { link: "Follow", value: "Follow", isActive: false },
];

const HomeScreen = () => {
  // Default to "Discover" with the correct case
  const [activePage, setActivePage] = useState<string>("Discover");

  // Map link values to components
  const pageComponents: { [key: string]: React.ComponentType } = {
    Follow: Following, // Ensure the key matches "link" from columnHeaders
    Discover, // Matches the key in columnHeaders
  };

  return (
    <View style={{ flex: 1 }}>
      <Dropdown
        headers={columnHeaders}
        navigation={{
          navigate: (link: string) => setActivePage(link), // Update the active page
        }}
      />
      <View style={{ flex: 1, padding: 20 }}>
        {/* Render the active component, or fallback if undefined */}
        {activePage && pageComponents[activePage] ? (
          React.createElement(pageComponents[activePage])
        ) : (
          <Text>Page not found</Text>
        )}
      </View>
    </View>
  );
};

export default HomeScreen;
