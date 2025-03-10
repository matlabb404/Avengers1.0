import { StyleSheet } from "react-native";
import theme from "@/styles/theme";

const styles = StyleSheet.create({
    headerText: {
        fontSize: theme.sizes.medium,
        fontWeight: 600,
    },
    headerBox: {
        flexDirection: 'row',
        backgroundColor: theme.colors.highlight,
        height: theme.sizes.xxlarge,
        width: '100%',
        padding:0,
        marginTop: 15,
        justifyContent: 'center',
        borderRadius: theme.sizes.xxsmall,
        borderWidth: 2,
        borderColor: theme.colors.highlight,
    },
    headerContainer: {
        paddingLeft: theme.sizes.xsmall,
        paddingRight: theme.sizes.xsmall,
        justifyContent: 'center',
        width: '50%',
    },
    activeButton: {
        paddingRight: theme.sizes.xsmall,
        paddingLeft: theme.sizes.xsmall,
        justifyContent: 'center',
        backgroundColor: theme.colors.primary,
        borderRadius: theme.sizes.xxxsmall,
    },
});

export default styles;