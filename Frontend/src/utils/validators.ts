/**
 * Form and data validators
 */

/**
 * Validate email format
 */
export function validateEmail(email: string): boolean {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
}

/**
 * Validate phone number format (basic validation)
 */
export function validatePhoneNumber(phone: string): boolean {
  const cleaned = phone.replace(/\D/g, "");
  return cleaned.length >= 10 && cleaned.length <= 15;
}

/**
 * Validate required field
 */
export function validateRequired(value: string | unknown[]): boolean {
  if (typeof value === "string") {
    return value.trim().length > 0;
  }
  if (Array.isArray(value)) {
    return value.length > 0;
  }
  return !!value;
}

/**
 * Validate minimum length
 */
export function validateMinLength(value: string, minLength: number): boolean {
  return value.length >= minLength;
}

/**
 * Validate maximum length
 */
export function validateMaxLength(value: string, maxLength: number): boolean {
  return value.length <= maxLength;
}

/**
 * Validate numeric range
 */
export function validateNumberRange(value: number, min: number, max: number): boolean {
  return value >= min && value <= max;
}

/**
 * Validate CSV headers match expected fields
 */
export function validateCsvHeaders(
  headers: string[],
  requiredFields: string[]
): { valid: boolean; missingFields: string[] } {
  const normalizedHeaders = headers.map((h) => h.toLowerCase().trim());
  const missingFields = requiredFields.filter(
    (field) => !normalizedHeaders.includes(field.toLowerCase())
  );
  return {
    valid: missingFields.length === 0,
    missingFields,
  };
}

/**
 * Validate phone number format (E.164)
 */
export function validateE164Phone(phone: string): boolean {
  const e164Regex = /^\+?[1-9]\d{1,14}$/;
  return e164Regex.test(phone.replace(/\D/g, ""));
}
