import { useLayoutEffect, useRef, useState } from "react";
import { TextField, type TextFieldProps } from "@mui/material";
import { moneyInputValue, normalizeMoney, toEnglishDigits } from "./numberUtils";

type MoneyFieldProps = Omit<TextFieldProps, "value" | "onChange" | "type"> & {
  valueRial: number;
  onValueRialChange: (valueRial: number) => void;
};

export function MoneyField({ valueRial, onValueRialChange, slotProps, ...props }: MoneyFieldProps) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const digitsRightOfCaret = useRef<number | null>(null);
  const [editRevision, setEditRevision] = useState(0);

  useLayoutEffect(() => {
    const input = inputRef.current;
    const digitsRight = digitsRightOfCaret.current;
    if (!input || digitsRight === null) return;
    digitsRightOfCaret.current = null;
    let position = input.value.length;
    let seen = 0;
    while (position > 0 && seen < digitsRight) {
      position -= 1;
      if (/\d/.test(toEnglishDigits(input.value[position]))) seen += 1;
    }
    input.setSelectionRange(position, position);
  }, [valueRial, editRevision]);

  return (
    <TextField
      {...props}
      value={moneyInputValue(valueRial)}
      onChange={(event) => {
        const caret = event.target.selectionStart ?? event.target.value.length;
        digitsRightOfCaret.current = toEnglishDigits(event.target.value.slice(caret)).replace(/\D/g, "").length;
        setEditRevision((current) => current + 1);
        onValueRialChange(normalizeMoney(event.target.value));
      }}
      inputMode="numeric"
      slotProps={{ ...slotProps, htmlInput: { inputMode: "numeric", dir: "ltr", ...slotProps?.htmlInput, ref: inputRef } }}
    />
  );
}
