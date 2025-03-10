import { TOGGLE_DROPDOWN, OPEN_DROPDOWN, CLOSE_DROPDOWN } from '../constants';

export function toggleDropdown() {
  console.log(TOGGLE_DROPDOWN);
  return {
    type: TOGGLE_DROPDOWN,
  };
}

export function openDropdown() {
  console.log(OPEN_DROPDOWN);
  return {
    type: OPEN_DROPDOWN,
  };
}

export function closeDropdown() {
  console.log(CLOSE_DROPDOWN);
  return {
    type: CLOSE_DROPDOWN,
  };
}
