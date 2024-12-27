import { StyleSheet } from "react-native";
import theme from "@/styles/theme";

const styles = StyleSheet.create({
    main: {
        height: 80,
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
        marginTop: 25,
        width: '100%',
        paddingLeft: '5%',
        paddingRight: '5%',
        justifyContent: 'space-between',
        overflowX: 'hidden',
    },
    iconBox: { 
        width: '20%', 
        minWidth: 145,
        flexDirection: 'row', 
        justifyContent: 'space-between',
        overflowX: 'hidden',
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
        borderRadius: theme.sizes.xxxsmall,
    },
    backdrop: {
        backgroundColor: theme.colors.highlight,
        zIndex: -5,
    },
});

export default styles;