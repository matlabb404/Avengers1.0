import { StyleSheet } from "react-native";
import theme from "@/styles/theme";

const styles = StyleSheet.create({
  dropdownContainer: {
    zIndex: 100, // Make sure the dropdown is above other content
  },
  activePage: {
    flex: 1,
    padding: 20,
    marginTop: 80,
    zIndex: 40, // Make sure the dropdown is above other content
  },
});

export default styles;