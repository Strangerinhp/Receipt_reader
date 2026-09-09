import React, { useState } from "react";

const OCRContext = React.createContext({
  activePage: 0,
  file: null,
  draft: null,
  savedId: null,
  setActivePage: (activePage) => {},
  setFile: (file) => {},
  setDraft: (draft) => {},
  setSavedId: (invoiceId) => {},
  reset: () => {},
});

export const OCRContextProvider = (props) => {
  const [activePage, setActivePage] = useState(0);
  const [file, setFile] = useState(null);
  const [draft, setDraft] = useState(null);
  const [savedId, setSavedId] = useState(null);

  const pageHandler = (activePage) => {
    setActivePage(activePage);
  };

  const reset = () => {
    setActivePage(0);
    setFile(null);
    setDraft(null);
    setSavedId(null);
  };

  const contextValue = {
    activePage: activePage,
    file: file,
    draft: draft,
    savedId: savedId,
    setActivePage: pageHandler,
    setFile: setFile,
    setDraft: setDraft,
    setSavedId: setSavedId,
    reset: reset,
  };

  return <OCRContext.Provider value={contextValue}>{props.children}</OCRContext.Provider>;
};

export default OCRContext;
