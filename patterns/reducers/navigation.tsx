import { TOGGLE_DROPDOWN, OPEN_DROPDOWN, CLOSE_DROPDOWN } from '../constants';

const initialState = {
  dropdownOpened: false,
  dropdownStatic: true,
};

export default function navigation(state = initialState, action: { type: any; }) {
  switch (action.type) {
    case TOGGLE_DROPDOWN:
      return {
        ...state,
        dropdownOpened: !state.dropdownOpened,
        dropdownStatic: !state.dropdownStatic,
      };
    case OPEN_DROPDOWN:
      return {
        ...state,
        dropdownOpened: true,
        dropdownStatic: true,
      };
    case CLOSE_DROPDOWN:
      return {
        ...state,
        dropdownOpened: false,
        dropdownStatic: true,
      };
    default:
      return state;
  }
}
