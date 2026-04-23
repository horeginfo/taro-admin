const SHEET_NAME = "Luckyspin";
const START_ROW = 6;

function doPost(e) {
  try {
    const sheet = SpreadsheetApp.openById("1V1O_YSzl1xnx-rhpVqOXZsF7QvwJQVmv4HUPbootOUc").getSheetByName(SHEET_NAME);
    if (!sheet) {
      return jsonResponse({
        ok: false,
        message: "Sheet tidak ditemukan"
      });
    }

    const body = JSON.parse(e.postData.contents || "{}");
    const action = String(body.action || "claim_code").trim();
    const userId = normalizeText(body.user_id);
    const teleId = normalizeText(body.tele_id);

    if (action !== "claim_code") {
      return jsonResponse({
        ok: false,
        message: "Action tidak valid"
      });
    }

    if (!userId) {
      return jsonResponse({
        ok: false,
        message: "User ID kosong"
      });
    }

    const lastRow = sheet.getLastRow();
    if (lastRow < START_ROW) {
      return jsonResponse({
        ok: false,
        message: "Data kode belum ada di sheet"
      });
    }

    const totalRows = lastRow - START_ROW + 1;

    // Ambil kolom B sampai F:
    // B = kode, C = nominal, D = user id, E = tele id, F = waktu klaim
    const values = sheet.getRange(START_ROW, 2, totalRows, 5).getValues();

    // 1. Cek apakah user_id atau tele_id sudah pernah klaim
    for (let i = 0; i < values.length; i++) {
      const existingUserId = normalizeText(values[i][2]); // kolom D
      const existingTeleId = normalizeText(values[i][3]); // kolom E
      const isSameUserId = existingUserId && existingUserId.toLowerCase() === userId.toLowerCase();
      const isSameTeleId = existingTeleId && existingTeleId === teleId;

      if (isSameUserId || isSameTeleId) {
        return jsonResponse({
          ok: false,
          status: "already_claimed",
          message: "Lucky spin dapat di klaim 1 kali dalam 1 hari , info selanjutnya bisa Hub admin @horeg222"
        });
      }
    }

    // 2. Cari kode pertama yang belum dipakai
    for (let i = 0; i < values.length; i++) {
      const rowIndex = START_ROW + i;
      const kode = normalizeText(values[i][0]);      // kolom B
      const nominal = values[i][1];                  // kolom C
      const existingUserId = normalizeText(values[i][2]); // kolom D

      if (kode && !existingUserId) {
        const now = new Date();

        sheet.getRange(rowIndex, 4).setValue(userId);   // D = USER ID
        sheet.getRange(rowIndex, 5).setValue(teleId);   // E = TELE ID
        sheet.getRange(rowIndex, 6).setValue(now);      // F = WAKTU KLAIM

        return jsonResponse({
          ok: true,
          status: "success",
          message: "Kode akses berhasil diambil",
          data: {
            kode: kode,
            nominal: nominal,
            user_id: userId,
            tele_id: teleId,
            row: rowIndex
          }
        });
      }
    }

    return jsonResponse({
      ok: false,
      status: "no_code_available",
      message: "Kode akses sedang habis, silakan coba lagi nanti"
    });

  } catch (err) {
    return jsonResponse({
      ok: false,
      status: "error",
      message: String(err)
    });
  }
}

function doGet() {
  return jsonResponse({
    ok: true,
    message: "Apps Script aktif"
  });
}

function normalizeText(value) {
  return String(value || "").trim();
}

function jsonResponse(payload) {
  return ContentService
    .createTextOutput(JSON.stringify(payload))
    .setMimeType(ContentService.MimeType.JSON);
}
