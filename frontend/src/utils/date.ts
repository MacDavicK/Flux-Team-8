export function format(date: Date, format: string): string {
  const months = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
  ];

  const day = date.getDate();
  const month = months[date.getMonth()];
  const year = date.getFullYear();

  // Add ordinal suffix to day
  const ordinal = (n: number): string => {
    const s = ["th", "st", "nd", "rd"];
    const v = n % 100;
    return n + (s[(v - 20) % 10] || s[v] || s[0]);
  };

  if (format === "MMMM do") {
    return `${month} ${ordinal(day)}`;
  }

  if (format === "MMMM do, yyyy") {
    return `${month} ${ordinal(day)}, ${year}`;
  }

  return date.toLocaleDateString();
}
