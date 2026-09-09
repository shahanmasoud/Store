import { useLayoutEffect, useRef, useState } from "react";
import { TextField, type TextFieldProps } from "@mui/material";
import { canonicalDecimalInput, formatDecimalInput, toEnglishDigits } from "./numberUtils";

type LocalizedDecimalFieldProps = Omit<TextFieldProps, "value" | "onChange" | "type"> & {
  /** ASCII digits with an optional dot and no grouping separators. */
  value: string;
  onValueChange: (canonicalValue: string) => void;
};

export function LocalizedDecimalField({ value, onValueChange, slotProps, ...props }: LocalizedDecimalFieldProps) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const tokensRightOfCaret = useRef<number | null>(null);
  const [editRevision, setEditRevision] = useState(0);

  useLayoutEffect(() => {
    const input = inputRef.current;
    const tokensRight = tokensRightOfCaret.current;
    if (!input || tokensRight === null) return;
    tokensRightOfCaret.current = null;
    let position = input.value.length;
    let seen = 0;
    while (position > 0 && seen < tokensRight) {
      position -= 1;
      if (/[\d.]/.test(toEnglishDigits(input.value[position]).replace("٫", "."))) seen += 1;
    }
    input.setSelectionRange(position, position);
  }, [value, editRevision]);

  return (
    <TextField
      {...props}
      value={formatDecimalInput(value)}
      onChange={(event) => {
        const caret = event.target.selectionStart ?? event.target.value.length;
        tokensRightOfCaret.current = toEnglishDigits(event.target.value.slice(caret))
          .replace(/٫/g, ".")
          .replace(/[^\d.]/g, "").length;
        setEditRevision((current) => current + 1);
        onValueChange(canonicalDecimalInput(event.target.value));
      }}
      slotProps={{ ...slotProps, htmlInput: { inputMode: "decimal", dir: "ltr", ...slotProps?.htmlInput, ref: inputRef } }}
    />
  );
}
