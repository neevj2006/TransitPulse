import { ImageResponse } from "next/og";

export const size = { width: 512, height: 512 };
export const contentType = "image/png";

export default function Icon() {
  return new ImageResponse(
    <div
      style={{
        alignItems: "center",
        background: "#1859C9",
        display: "flex",
        height: "100%",
        justifyContent: "center",
        width: "100%",
      }}
    >
      <div
        style={{
          alignItems: "center",
          border: "28px solid #FFFFFF",
          borderRadius: 72,
          color: "#FFFFFF",
          display: "flex",
          fontFamily: "sans-serif",
          fontSize: 210,
          fontWeight: 700,
          height: 356,
          justifyContent: "center",
          width: 356,
        }}
      >
        T
      </div>
    </div>,
    { ...size },
  );
}
