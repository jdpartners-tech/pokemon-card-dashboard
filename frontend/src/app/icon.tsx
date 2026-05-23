import { ImageResponse } from "next/og";

export const size = { width: 32, height: 32 };
export const contentType = "image/png";

export default function Icon() {
  return new ImageResponse(
    (
      <div
        style={{
          background: "#0f172a",
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          borderRadius: 6,
        }}
      >
        <div
          style={{
            width: 22,
            height: 22,
            borderRadius: 11,
            border: "2px solid #475569",
            overflow: "hidden",
            display: "flex",
            flexDirection: "column",
            position: "relative",
          }}
        >
          <div style={{ flex: 1, background: "#dc2626", display: "flex" }} />
          <div style={{ flex: 1, background: "#e2e8f0", display: "flex" }} />
          <div
            style={{
              position: "absolute",
              top: 9,
              left: 0,
              right: 0,
              height: 4,
              background: "#334155",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <div
              style={{
                width: 6,
                height: 6,
                borderRadius: 3,
                background: "#e2e8f0",
                border: "1px solid #334155",
                display: "flex",
              }}
            />
          </div>
        </div>
      </div>
    ),
    { ...size }
  );
}
