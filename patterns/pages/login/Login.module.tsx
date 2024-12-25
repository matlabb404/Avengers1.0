import { StyleSheet } from "react-native";

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: "center",
    padding: 16,
  },
  title: {
    fontSize: 24,
    textAlign: "center",
    marginBottom: 24,
  },
  input: {
    borderRadius: 8,
    height: 40,
    borderColor: "#ccc",
    borderWidth: 1,
    marginBottom: 12,
    paddingLeft: 8,
  },
  error: {
    color: "red",
    marginBottom: 12,
  },
  button: {
    backgroundColor: "#32a5db",
    height: 40,
    justifyContent: "center",
    marginBottom: 8,
    borderBottomLeftRadius: 10,
    borderTopRightRadius: 10,
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
    fontSize: 18,
  },
  toggleButton: {
    marginLeft: 10,
    marginRight: 15,
  },
  toggleText: {
    color: "#32a5db",
    fontWeight: "bold",
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
