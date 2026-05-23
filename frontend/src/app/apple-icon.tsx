import { ImageResponse } from "next/og";

export const size = { width: 180, height: 180 };
export const contentType = "image/png";

export default function AppleIcon() {
  return new ImageResponse(
    (
      <div
        style={{
          background: "linear-gradient(135deg, #0f172a 0%, #1e293b 100%)",
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        {/* Pokéball */}
        <div
          style={{
            width: 130,
            height: 130,
            borderRadius: 65,
            border: "8px solid #334155",
            overflow: "hidden",
            display: "flex",
            flexDirection: "column",
            position: "relative",
          }}
        >
          {/* Top red half */}
          <div style={{ flex: 1, background: "#dc2626", display: "flex" }} />
          {/* Bottom white half */}
          <div style={{ flex: 1, background: "#f1f5f9", display: "flex" }} />
          {/* Centre band + button — top: 57 centres a 16px stripe at the 130px circle midpoint */}
          <div
            style={{
              position: "absolute",
              top: 57,
              left: 0,
              right: 0,
              height: 16,
              background: "#1e293b",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <div
              style={{
                width: 30,
                height: 30,
                borderRadius: 15,
                background: "#f1f5f9",
                border: "6px solid #1e293b",
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
