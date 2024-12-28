import React, { useState } from "react";
import { View } from "react-native";
import Dropdown from "@/components/Dropdown/Dropdown";
// import Register from "@/pages/register/Register"; // Import the components for each link
// import Login from "@/pages/login/Login"; // Import the components for each link
import Following from "../follow/Follow";
import Discover from "../discover/Discover";
import Footer from "@/components/Footer/Footer";
import styles from "./homescreen.style";

// Define the column headers
const columnHeaders = [
  { link: "Discover", value: "Discover", isActive: true },
  { link: "Following", value: "Follow", isActive: false },
];

const HomeScreen = () => {
  const [activePage, setActivePage] = useState<string>("Discover"); // Default page

  // Map link values to components
  const pageComponents: { [key: string]: React.ComponentType } = {
    Following,
    Discover,
  };

  return (
    <View style={{ flex: 1 }}>
       {/* Dropdown component positioned at the top */}
       <View style={styles.dropdownContainer}>
        <Dropdown
          headers={columnHeaders}
          navigation={{
            navigate: (link: string) => setActivePage(link), // Update the active page
          }}
        />
      </View>
      <View style={styles.activePage}>
        {/* Render the active component */}
        {activePage && React.createElement(pageComponents[activePage])}
      </View>
      {/* Footer component positioned at the bottom */}
      <Footer/>
    </View>
  );
};

export default HomeScreen;
