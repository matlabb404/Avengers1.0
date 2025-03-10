import { StyleSheet } from "react-native";
import theme from "@/styles/theme";

const styles = StyleSheet.create({
    mainfoot: {
        backgroundColor: theme.colors.primary,
        position: 'absolute',
        bottom: 0,
        left: 0,
        right: 0,
        width: '100%',
        height: 100,
        justifyContent: 'center',
        borderTopLeftRadius: theme.sizes.small,
        borderTopRightRadius: theme.sizes.small,
        borderTopWidth: 3,
        borderColor: theme.colors.highlight,
    },
    iconContainer:{
        flexDirection: 'row',
        justifyContent: 'space-between',
        width: '90%',
        margin: 'auto',
    },
    activeButton: {
        borderBottomWidth: 2,
        borderBottomColor: "#007BFF",
      },
      inactiveButton: {
        borderBottomWidth: 0,
      },
      activeText: {
        color: "#007BFF",
        fontWeight: "bold",
      },
      inactiveText: {
        color: "#000",
      },
});

export default styles;