import { StyleSheet } from "react-native";
import theme from "../../styles/theme";

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: "center",
    padding: theme.sizes.medium,
  },
  title: {
    color: theme.colors.font,
    fontSize: theme.sizes.xlarge,
    textAlign: "center",
    marginBottom: theme.sizes.xlarge,
  },
  input: {
    borderRadius: theme.sizes.small,
    height: theme.sizes.xxxlarge,
    borderColor: "#ccc",
    borderWidth: 1,
    marginBottom: theme.sizes.small,
    paddingLeft: theme.sizes.xxsmall,
  },
  error: {
    color: theme.colors.danger,
    marginBottom: theme.sizes.small,
    textAlign: "center",
    margin: 0,
    padding: 0,
  },
  button: {
    backgroundColor: "#32a5db",
    height: theme.sizes.xxxlarge,
    justifyContent: "center",
    marginBottom: theme.sizes.xxsmall,
    borderBottomLeftRadius: theme.sizes.xsmall,
    borderTopRightRadius: theme.sizes.xsmall,
  },
  password: {
    borderColor: "#ccc",
    borderRightWidth: 1,
    paddingLeft: 5,
    width: 300,
  },
  text: {
    textAlign: "center",
    color: "white",
    fontSize: theme.sizes.medium,
  },
  toggleButton: {
    marginLeft: 10,
    marginRight: 15,
  },
  toggleText: {
    fontWeight: "bold",
    color: theme.colors.font,
  },
  passwordContainer: {
    flexDirection: "row",
    alignItems: "center",
    borderColor: "#ccc",
    borderWidth: 1,
    marginBottom: 16,
    borderRadius: 8,
    height: 40,
    justifyContent: 'space-between',
  },
});

export default styles;
