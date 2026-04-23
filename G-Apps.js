const SHEET_NAME = "Luckyspin";
const START_ROW = 6;
const DAILY_LIMIT_MAX_NUMBER = 100;
const DAILY_LIMIT_MESSAGE = "Maaf Ya Bonus Lucky Spin untuk Hari ini sudah Limit yaa !!\ninfo lebih lanjut bisa Tanya ke admin @horeg222";

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

    // Ambil kolom A sampai F:
    // A = nomor urut, B = kode, C = nominal, D = user id, E = tele id, F = waktu klaim
    const values = sheet.getRange(START_ROW, 1, totalRows, 6).getValues();
    const limitedRows = values
      .map((row, index) => ({
        rowIndex: START_ROW + index,
        number: normalizeNumber(row[0]),
        kode: normalizeText(row[1]),
        nominal: row[2],
        existingUserId: normalizeText(row[3]),
        existingTeleId: normalizeText(row[4]),
        claimedAt: row[5]
      }))
      .filter((row) => row.number >= 1 && row.number <= DAILY_LIMIT_MAX_NUMBER);

    if (limitedRows.length === 0) {
      return jsonResponse({
        ok: false,
        status: "no_limited_rows",
        message: "Data Lucky Spin nomor 1 sampai 100 belum tersedia di sheet"
      });
    }

    const isDailyLimitReached = limitedRows.every((row) => (
      row.existingUserId && row.existingTeleId && !isEmptyValue(row.claimedAt)
    ));

    if (isDailyLimitReached) {
      return jsonResponse({
        ok: false,
        status: "daily_limit_reached",
        message: DAILY_LIMIT_MESSAGE
      });
    }

    // 1. Cek apakah user_id atau tele_id sudah pernah klaim
    for (let i = 0; i < limitedRows.length; i++) {
      const existingUserId = limitedRows[i].existingUserId;
      const existingTeleId = limitedRows[i].existingTeleId;
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
    for (let i = 0; i < limitedRows.length; i++) {
      const rowIndex = limitedRows[i].rowIndex;
      const kode = limitedRows[i].kode;
      const nominal = limitedRows[i].nominal;
      const existingUserId = limitedRows[i].existingUserId;

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

function normalizeNumber(value) {
  const parsed = Number(String(value || "").trim());
  return Number.isFinite(parsed) ? parsed : NaN;
}

function isEmptyValue(value) {
  return value === "" || value === null || typeof value === "undefined";
}

function jsonResponse(payload) {
  return ContentService
    .createTextOutput(JSON.stringify(payload))
    .setMimeType(ContentService.MimeType.JSON);
}
