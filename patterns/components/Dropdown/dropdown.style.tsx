import { StyleSheet } from "react-native";
import theme from "@/styles/theme";

const styles = StyleSheet.create({
    main: {
        height: 75,
        margin: 0,
        padding: 0,
        width: '100%',
        borderBottomWidth: 4,
        borderBottomColor: theme.colors.shadowM,
        borderBottomLeftRadius: theme.sizes.xxsmall,
        borderBottomRightRadius: theme.sizes.xxsmall,
        backgroundColor: theme.colors.primary,
    },
    TopBox: {
        flexDirection: 'row',
        padding: 0,
        height: 50,
        marginTop: 20,
        width: '90%',
        marginLeft: '5%',
        marginRight: '5%',
    },
    headerBox: {
        flexDirection: 'row',
        backgroundColor: theme.colors.secondary,
        height: theme.sizes.xxlarge,
        padding:0,
        marginTop: 5,
        marginLeft: 5,
        justifyContent: 'center',
        borderRadius: theme.sizes.xxsmall,
        borderWidth: 2,
        borderColor: theme.colors.secondary,
    },
    headerText: {
        fontSize: theme.sizes.medium,
        fontWeight: 600,
    },
    headerContainer: {
        paddingLeft: theme.sizes.xsmall,
        paddingRight: theme.sizes.xsmall,
        justifyContent: 'center',
    },
    activeButton: {
        paddingRight: theme.sizes.xsmall,
        paddingLeft: theme.sizes.xsmall,
        justifyContent: 'center',
        backgroundColor: theme.colors.primary,
        borderRadius: theme.sizes.xxsmall,
    }
});

export default styles;