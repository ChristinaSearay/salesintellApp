// Shrink a photo on the phone before it is uploaded.
//
// A phone camera shot is 3–5 MB; at 1600px it is ~300 KB and still sharp
// enough to judge a shop's displays, so uploads stay quick on mobile data and
// the engine's disk lasts. Re-encoding through a canvas also drops the EXIF
// block — including the GPS position the camera stamped on it.
// Limits on the engine side: constants/photos.py.

export const PHOTO = {
  FULL_SIDE: 1600,
  THUMB_SIDE: 400,
  QUALITY: 0.82,
  TYPE: "image/jpeg",
  MAX_CAPTION: 200,   // MAX_CAPTION_CHARS in constants/photos.py
};

function loadImage(file) {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const img = new Image();
    // Browsers apply the camera's EXIF rotation when drawing an <img>.
    img.onload = () => { URL.revokeObjectURL(url); resolve(img); };
    img.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error("Couldn’t open that photo — try taking it again."));
    };
    img.src = url;
  });
}

function encode(img, maxSide) {
  const scale = Math.min(1, maxSide / Math.max(img.naturalWidth, img.naturalHeight));
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(img.naturalWidth * scale);
  canvas.height = Math.round(img.naturalHeight * scale);
  canvas.getContext("2d").drawImage(img, 0, 0, canvas.width, canvas.height);
  // data:image/jpeg;base64,<payload> → just the payload
  return canvas.toDataURL(PHOTO.TYPE, PHOTO.QUALITY).split(",")[1];
}

// → { image, thumb, preview }: base64 JPEGs for the engine + a data URL to show.
export async function shrinkPhoto(file) {
  if (!file.type.startsWith("image/")) throw new Error("That file isn’t a photo.");
  const img = await loadImage(file);
  const image = encode(img, PHOTO.FULL_SIDE);
  return { image, thumb: encode(img, PHOTO.THUMB_SIDE), preview: `data:${PHOTO.TYPE};base64,${image}` };
}
